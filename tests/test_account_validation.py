"""What finance-accounts refuses: unknown kinds, oversize names, non-object metadata, backwards dates."""

from accounts_helpers import ACCOUNTS, create


def test_account_type_must_be_a_known_kind(client, owner):
    response = create(client, owner, name="Mystery", account_type="crypto-vault")
    assert response.status_code == 422


def test_name_is_required(client, owner):
    response = client.post(ACCOUNTS, headers=owner, json={"account_type": "cash"})
    assert response.status_code == 422


def test_name_is_limited_to_200_characters(client, owner):
    assert create(client, owner, name="x" * 201).status_code == 422
    assert create(client, owner, name="y" * 200).status_code == 201


def test_currency_code_is_at_most_12_characters(client, owner):
    assert create(client, owner, name="Long ccy", currency="C" * 13).status_code == 422
    assert create(client, owner, name="USD acct", currency="USD").status_code == 201


def test_metadata_must_be_an_object(client, owner):
    response = create(client, owner, name="Wallet", metadata=["not", "an", "object"])
    assert response.status_code == 422


def test_an_account_cannot_close_before_it_opened(client, owner):
    early = create(
        client, owner, name="Backwards", opened_on="2026-05-01", closed_on="2026-04-30"
    )
    assert early.status_code == 422, early.text
    assert early.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["closed_on", "opened_on"],
    }
    same_day = create(
        client, owner, name="Same day", opened_on="2026-05-01", closed_on="2026-05-01"
    )
    assert same_day.status_code == 201, same_day.text


def test_closing_before_the_opening_date_is_refused_on_update(client, owner):
    account = create(client, owner, name="Opened in May", opened_on="2026-05-01").json()
    path = f"{ACCOUNTS}/{account['id']}"
    refused = client.patch(path, headers=owner, json={"closed_on": "2026-04-01"})
    assert refused.status_code == 422, refused.text
    assert client.get(path, headers=owner).json()["closed_on"] is None
    # A patch that touches neither date still works.
    renamed = client.patch(path, headers=owner, json={"name": "Renamed"})
    assert renamed.status_code == 200, renamed.text
