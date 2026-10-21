"""Defaults and uniqueness of a finance account."""

from accounts_helpers import create


def test_new_account_defaults_to_personal_active_thb(client, owner):
    response = create(client, owner, name="Kbank savings")
    assert response.status_code == 201, response.text
    account = response.json()
    assert account["currency"] == "THB"
    assert account["owner_scope"] == "personal"
    assert account["status"] == "active"
    assert account["version"] == 1


def test_name_is_unique_within_an_owner_scope(client, owner):
    assert create(client, owner, name="Cash box").status_code == 201
    assert create(client, owner, name="Cash box").status_code == 409
    other_scope = create(client, owner, name="Cash box", owner_scope="venture")
    assert other_scope.status_code == 201, other_scope.text


def test_opening_balance_keeps_its_decimal_value(client, owner):
    account = create(client, owner, name="Float check", opening_balance=1234.56).json()
    assert account["opening_balance"] == 1234.56
