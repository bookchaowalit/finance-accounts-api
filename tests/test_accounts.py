"""Finance-accounts rules from cell.yaml, beyond the generic contract: defaults, enums, uniqueness."""

ACCOUNTS = "/v1/accounts"


def create(client, owner, **fields):
    return client.post(ACCOUNTS, headers=owner, json={"account_type": "bank", **fields})


def test_new_account_defaults_to_personal_active_thb(client, owner):
    response = create(client, owner, name="Kbank savings")
    assert response.status_code == 201, response.text
    account = response.json()
    assert account["currency"] == "THB"
    assert account["owner_scope"] == "personal"
    assert account["status"] == "active"


def test_account_type_must_be_a_known_kind(client, owner):
    response = create(client, owner, name="Mystery", account_type="crypto-vault")
    assert response.status_code == 422


def test_name_is_unique_within_an_owner_scope(client, owner):
    assert create(client, owner, name="Cash box").status_code == 201
    assert create(client, owner, name="Cash box").status_code == 409
    other_scope = create(client, owner, name="Cash box", owner_scope="venture")
    assert other_scope.status_code == 201, other_scope.text


def test_name_is_limited_to_200_characters(client, owner):
    assert create(client, owner, name="x" * 201).status_code == 422
    assert create(client, owner, name="y" * 200).status_code == 201


def test_metadata_must_be_an_object(client, owner):
    response = create(client, owner, name="Wallet", metadata=["not", "an", "object"])
    assert response.status_code == 422


def test_list_filters_by_account_type(client, owner):
    create(client, owner, name="Card A", account_type="credit")
    create(client, owner, name="Broker", account_type="investment")
    listed = client.get(ACCOUNTS, headers=owner, params={"account_type": "credit"})
    assert listed.status_code == 200, listed.text
    kinds = {item["account_type"] for item in listed.json()["items"]}
    assert kinds == {"credit"}


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
