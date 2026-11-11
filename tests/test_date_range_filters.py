"""SPEC-007: <field>_from / <field>_to bounds on date and timestamp fields (list, stats, MCP)."""

import uuid

import pytest
from accounts_helpers import ACCOUNTS, create

from cellkit.spec import SpecError, parse


def _names(client, owner, **params):
    listed = client.get(ACCOUNTS, headers=owner, params={"limit": 1000, **params})
    assert listed.status_code == 200, listed.text
    return {item["name"] for item in listed.json()["items"]}


@pytest.fixture
def opened(client, owner):
    """Three accounts opened on known days, one with no date; names are unique to this test run."""
    tag = uuid.uuid4().hex[:8]
    days = {
        "early": "2025-01-31",
        "mid": "2025-02-15",
        "late": "2025-03-01",
        "none": None,
    }
    for key, day in days.items():
        fields = {"name": f"{tag}-{key}"}
        if day:
            fields["opened_on"] = day
        assert create(client, owner, **fields).status_code == 201
    return tag


def test_from_and_to_are_inclusive_bounds(client, owner, opened):  # AC-01, AC-02
    t = opened
    mine = {f"{t}-early", f"{t}-mid", f"{t}-late", f"{t}-none"}
    got = _names(client, owner, opened_on_from="2025-02-15") & mine
    assert got == {f"{t}-mid", f"{t}-late"}
    got = _names(client, owner, opened_on_to="2025-02-15") & mine
    assert got == {f"{t}-early", f"{t}-mid"}
    got = (
        _names(client, owner, opened_on_from="2025-02-01", opened_on_to="2025-02-28")
        & mine
    )
    assert got == {f"{t}-mid"}


def test_bounds_combine_with_other_filters(client, owner, opened):  # AC-01
    t = opened
    got = _names(client, owner, opened_on_from="2025-01-01", account_type="credit") & {
        f"{t}-early",
        f"{t}-mid",
        f"{t}-late",
    }
    assert got == set()


def test_a_bound_that_does_not_parse_is_refused(client, owner):  # AC-04
    listed = client.get(
        ACCOUNTS, headers=owner, params={"opened_on_from": "15/02/2025"}
    )
    assert listed.status_code == 422
    assert listed.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["opened_on_from"],
    }


def test_from_after_to_is_refused(client, owner):  # AC-05
    listed = client.get(
        ACCOUNTS,
        headers=owner,
        params={"opened_on_from": "2025-03-01", "opened_on_to": "2025-02-01"},
    )
    assert listed.status_code == 422
    assert listed.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["opened_on_from", "opened_on_to"],
    }


def test_a_bound_on_a_non_date_field_is_unknown(client, owner):  # AC-06
    listed = client.get(ACCOUNTS, headers=owner, params={"name_from": "a"})
    assert listed.status_code == 422
    assert listed.json()["detail"]["error"] == "unknown_filter"


def test_stats_count_only_rows_inside_the_bounds(client, owner, opened):  # AC-07
    before = client.get(
        f"{ACCOUNTS}/stats",
        headers=owner,
        params={
            "group_by": "status",
            "opened_on_from": "2025-02-01",
            "opened_on_to": "2025-02-28",
        },
    )
    assert before.status_code == 200, before.text
    create(client, owner, name=f"{opened}-extra", opened_on="2025-02-20")
    create(client, owner, name=f"{opened}-outside", opened_on="2024-02-20")
    after = client.get(
        f"{ACCOUNTS}/stats",
        headers=owner,
        params={
            "group_by": "status",
            "opened_on_from": "2025-02-01",
            "opened_on_to": "2025-02-28",
        },
    )
    assert after.json()["groups"]["active"] == before.json()["groups"]["active"] + 1


def _demo(fields):
    return parse({"cell": "demo", "resources": {"item": {"fields": fields}}}).resource(
        "item"
    )


def test_timestamp_and_date_fields_get_bounds():  # AC-01, AC-03
    item = _demo(
        {"day": {"type": "date"}, "at": {"type": "timestamp"}, "n": {"type": "int"}}
    )
    assert set(item.bounds) == {"day_from", "day_to", "at_from", "at_to"}
    assert item.bounds["at_to"][1] == "<="


def test_mcp_list_takes_the_bounds():  # AC-08
    from cellkit.mcp import argument_models

    demo = parse(
        {"cell": "demo", "resources": {"item": {"fields": {"day": {"type": "date"}}}}}
    )
    listing = argument_models(demo, demo.resource("item"))["list"]
    checked = listing.model_validate({"day_from": "2025-01-01", "day_to": "2025-01-31"})
    assert (
        checked.model_dump(mode="json", exclude_none=True)["day_from"] == "2025-01-01"
    )


def test_a_field_named_like_a_bound_does_not_load():  # AC-09
    with pytest.raises(SpecError, match="day_from"):
        _demo({"day": {"type": "date"}, "day_from": {"type": "text"}})
