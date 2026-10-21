"""Shared helpers for the finance-accounts domain tests."""

from typing import Any

ACCOUNTS = "/v1/accounts"


def create(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    return client.post(ACCOUNTS, headers=owner, json={"account_type": "bank", **fields})
