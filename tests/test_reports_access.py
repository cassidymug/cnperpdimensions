import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User

client = TestClient(app)

# Utility to ensure seed roles/users exist (assumes seeding done on startup)

def login(username: str, password: str):
    r = client.post('/api/v1/auth/login-json', json={'username': username, 'password': password})
    return r

@pytest.mark.parametrize("username,password,expected", [
    ("superadmin", "ChangeMe!123", 200),  # super_admin seeded via create_superadmin script
    ("accts", "ChangeMe123", 200),        # accountant demo user
    ("mgr", "ChangeMe123", 200),          # manager demo user should pass require_any(accountant,manager)
])
def test_reports_trial_balance_access_allowed(username, password, expected):
    r = login(username, password)
    assert r.status_code == 200, f"Login failed for {username}: {r.text}"
    token = r.json()['access_token']
    headers = { 'Authorization': f"Bearer {token}" }
    resp = client.get('/api/v1/reports/trial-balance', headers=headers)
    assert resp.status_code == expected, resp.text

@pytest.mark.parametrize("username,password", [
    ("cashier", "ChangeMe123"),  # if a cashier demo user added later, expect denial
])
def test_reports_trial_balance_access_denied(username, password):
    r = login(username, password)
    if r.status_code != 200:
        pytest.skip(f"User {username} not present; skipping")
    token = r.json()['access_token']
    headers = { 'Authorization': f"Bearer {token}" }
    resp = client.get('/api/v1/reports/trial-balance', headers=headers)
    assert resp.status_code in (401,403), resp.text
