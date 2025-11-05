import pytest
from fastapi.testclient import TestClient
from app.main import app

class DummyUser:
    def __init__(self, role: str, branch_id: str = "branch-1"):
        self.id = "test-user"
        self.role = role
        self.branch_id = branch_id

def override_user(role):
    from app.core import security
    app.dependency_overrides[security.get_current_user] = lambda: DummyUser(role)

client = TestClient(app)

def teardown_function():
    app.dependency_overrides.clear()

def test_cashier_cannot_create_product():
    # Cashier (POS) read-only in inventory
    override_user('cashier')
    payload = {"name":"X","sku":"sku-x","selling_price":10,"cost_price":5}
    r = client.post('/api/v1/inventory/products', json=payload)
    assert r.status_code == 403, r.text

def test_manager_can_create_product():
    override_user('manager')
    payload = {"name":"Y","sku":"sku-y","selling_price":10,"cost_price":5}
    r = client.post('/api/v1/inventory/products', json=payload)
    # Accept 200 or 400 if SKU collision from prior test runs
    assert r.status_code in (200, 400), r.text

def test_pos_user_cannot_create_product():
    override_user('pos_user')
    payload = {"name":"Z","sku":"sku-z","selling_price":10,"cost_price":5}
    r = client.post('/api/v1/inventory/products', json=payload)
    assert r.status_code == 403, r.text