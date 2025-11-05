import pytest
from fastapi.testclient import TestClient
from fastapi import Depends
from app.main import app
from app.schemas.user import User

# Create a dummy user object
class DummyUser:
    def __init__(self, role: str):
        self.id = "test-user"
        self.role = role
        self.branch_id = "branch-1"

def override_get_current_user_factory(role: str):
    def _dep():
        return DummyUser(role)
    return _dep

client = TestClient(app)

@pytest.mark.parametrize("role,endpoint,status", [
    ("cashier", "/api/v1/banking/accounts", 403),  # cashier blocked from banking
    ("manager", "/api/v1/purchases/suppliers", 403),  # manager blocked from purchases (accountant only)
    # accountant now has universal access; remove prior denial case
])
def test_role_denials(role, endpoint, status):
    # Override dependency for this role
    from app.core import security
    app.dependency_overrides[security.get_current_user] = override_get_current_user_factory(role)
    r = client.get(endpoint)
    assert r.status_code == status, f"Expected {status} for role {role} on {endpoint}, got {r.status_code}: {r.text}"
    app.dependency_overrides.clear()

@pytest.mark.parametrize("role,endpoint", [
    ("accountant", "/api/v1/banking/accounts"),  # allowed (accountant universal)
    ("manager", "/api/v1/inventory/products"),   # allowed
])
def test_role_access(role, endpoint):
    from app.core import security
    app.dependency_overrides[security.get_current_user] = override_get_current_user_factory(role)
    r = client.get(endpoint)
    assert r.status_code in (200, 404), f"Unexpected denial for role {role} on {endpoint}: {r.status_code}"
    app.dependency_overrides.clear()
