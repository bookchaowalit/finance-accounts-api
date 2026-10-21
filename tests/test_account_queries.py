"""Listing, grouping and the lifecycle of a finance account."""

from accounts_helpers import ACCOUNTS, create


def test_list_filters_by_account_type(client, owner):
    create(client, owner, name="Card A", account_type="credit")
    create(client, owner, name="Broker", account_type="investment")
    listed = client.get(ACCOUNTS, headers=owner, params={"account_type": "credit"})
    assert listed.status_code == 200, listed.text
    kinds = {item["account_type"] for item in listed.json()["items"]}
    assert kinds == {"credit"}


def test_stats_count_accounts_per_status(client, owner):
    create(client, owner, name="Active one")
    create(client, owner, name="Paused one", status="paused")
    stats = client.get(
        f"{ACCOUNTS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert stats.status_code == 200, stats.text
    groups = stats.json()["groups"]
    assert groups["active"] >= 1
    assert groups["paused"] >= 1


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    stats = client.get(f"{ACCOUNTS}/stats", headers=owner, params={"group_by": "name"})
    assert stats.status_code == 422


def test_closing_an_account_keeps_its_history(client, owner):
    account = create(client, owner, name="Old bank", opened_on="2020-01-01").json()
    closed = client.patch(
        f"{ACCOUNTS}/{account['id']}",
        headers=owner,
        json={"status": "closed", "closed_on": "2026-10-01"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert closed.json()["opened_on"] == "2020-01-01"
    assert closed.json()["version"] == 2
