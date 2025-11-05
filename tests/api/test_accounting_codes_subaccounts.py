import uuid
from typing import Dict, Optional

import pytest

from app.models.accounting import AccountingCode


def _unique_code(prefix: str = "AC") -> str:
    """Generate a short unique account code within 20-character limit."""
    return f"{prefix}{uuid.uuid4().hex[:6]}"


def _account_payload(*, code: Optional[str] = None, name: Optional[str] = None,
                     account_type: str = "Asset", category: str = "Cash",
                     is_parent: bool = True) -> Dict[str, object]:
    return {
        "code": code or _unique_code(),
        "name": name or f"Account {uuid.uuid4().hex[:6]}",
        "account_type": account_type,
        "category": category,
        "is_parent": is_parent,
        "parent_id": None,
        "branch_id": None,
    }


def _sub_account_payload(*, code: Optional[str] = None, name: Optional[str] = None,
                         account_type: str = "Asset", category: str = "Cash") -> Dict[str, object]:
    return {
        "code": code or _unique_code("SB"),
        "name": name or f"SubAccount {uuid.uuid4().hex[:6]}",
        "account_type": account_type,
        "category": category,
        "branch_id": None,
    }


@pytest.mark.parametrize("account_type,category", [("Asset", "Cash"), ("Liability", "Current Liability")])
def test_sub_account_lifecycle(client, db_session, account_type, category):
    """End-to-end coverage for creating, listing, and deleting a sub-account."""
    # Create parent account via API
    parent_response = client.post(
        "/api/v1/accounting-codes/",
        json=_account_payload(account_type=account_type, category=category),
    )
    assert parent_response.status_code == 201, parent_response.text
    parent_data = parent_response.json()

    # Create a sub-account under the parent
    sub_response = client.post(
        f"/api/v1/accounting-codes/{parent_data['id']}/sub-accounts",
        json=_sub_account_payload(account_type=account_type, category=category),
    )
    assert sub_response.status_code == 201, sub_response.text
    sub_data = sub_response.json()
    assert sub_data["parent_id"] == parent_data["id"]

    # Retrieve sub-accounts and verify presence
    list_response = client.get(f"/api/v1/accounting-codes/{parent_data['id']}/sub-accounts")
    assert list_response.status_code == 200
    sub_accounts = list_response.json()
    assert len(sub_accounts) == 1
    assert sub_accounts[0]["id"] == sub_data["id"]

    # Parent should now be flagged as a parent account
    db_session.expire_all()
    parent_in_db = db_session.get(AccountingCode, parent_data["id"])
    assert parent_in_db is not None
    assert parent_in_db.is_parent is True

    # Delete the sub-account
    delete_response = client.delete(
        f"/api/v1/accounting-codes/{parent_data['id']}/sub-accounts/{sub_data['id']}"
    )
    assert delete_response.status_code == 204

    # Ensure the sub-account is removed and parent flag toggled back
    db_session.expire_all()
    sub_in_db = db_session.get(AccountingCode, sub_data["id"])
    assert sub_in_db is None

    parent_after_delete = db_session.get(AccountingCode, parent_data["id"])
    assert parent_after_delete is not None
    assert parent_after_delete.is_parent is False

    # Listing sub-accounts should now return an empty list
    list_after_delete = client.get(f"/api/v1/accounting-codes/{parent_data['id']}/sub-accounts")
    assert list_after_delete.status_code == 200
    assert list_after_delete.json() == []


def test_delete_sub_account_requires_correct_parent(client, db_session):
    """Deleting with mismatched parent should not remove the sub-account."""
    parent_one = client.post(
        "/api/v1/accounting-codes/",
        json=_account_payload(code=_unique_code("P1"), name="Parent One"),
    ).json()

    parent_two = client.post(
        "/api/v1/accounting-codes/",
        json=_account_payload(code=_unique_code("P2"), name="Parent Two"),
    ).json()

    sub_account = client.post(
        f"/api/v1/accounting-codes/{parent_one['id']}/sub-accounts",
        json=_sub_account_payload(name="Child")
    ).json()

    # Attempt to delete the sub-account using the wrong parent ID
    wrong_delete = client.delete(
        f"/api/v1/accounting-codes/{parent_two['id']}/sub-accounts/{sub_account['id']}"
    )
    assert wrong_delete.status_code == 404
    error_payload = wrong_delete.json()
    message = error_payload.get("detail") or error_payload.get("message")
    assert message is not None
    assert "sub-account" in message.lower()

    # Sub-account should still exist in the database
    db_session.expire_all()
    child_in_db = db_session.get(AccountingCode, sub_account["id"])
    assert child_in_db is not None
    assert child_in_db.parent_id == parent_one["id"]

    # Ensure the correct parent still sees the child
    list_response = client.get(f"/api/v1/accounting-codes/{parent_one['id']}/sub-accounts")
    assert list_response.status_code == 200
    assert [child["id"] for child in list_response.json()] == [sub_account["id"]]

    # Clean up by deleting using the correct parent
    final_delete = client.delete(
        f"/api/v1/accounting-codes/{parent_one['id']}/sub-accounts/{sub_account['id']}"
    )
    assert final_delete.status_code == 204