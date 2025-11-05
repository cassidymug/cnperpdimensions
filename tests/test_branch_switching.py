import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.branch import Branch

client = TestClient(app)

def get_credentials():
    db = SessionLocal()
    try:
        superadmin = db.query(User).filter(User.username=='superadmin').first()
        admin = db.query(User).filter(User.username=='admin').first()
        branch = db.query(Branch).first()
        return superadmin, admin, branch
    finally:
        db.close()

def login_json(username, password):
    r = client.post('/api/v1/auth/login-json', json={'username':username,'password':password})
    assert r.status_code == 200, r.text
    return r.json()

def test_superadmin_can_switch_branch():
    superadmin, _, branch = get_credentials()
    if not superadmin or not branch:
        return
    # login
    tok = login_json('superadmin','superadminpassword')
    headers = {'Authorization': f"Bearer {tok['access_token']}"}
    # switch
    r = client.post('/api/v1/auth/switch-branch', json={'branch_id': branch.id}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['branch_id'] == branch.id


def test_admin_gets_audit_log_on_switch():
    _, admin, branch = get_credentials()
    if not admin or not branch:
        return
    tok = login_json('admin','adminpassword')
    headers = {'Authorization': f"Bearer {tok['access_token']}"}
    r = client.post('/api/v1/auth/switch-branch', json={'branch_id': branch.id}, headers=headers)
    assert r.status_code == 200
    # fetch audit logs
    logs = client.get('/api/v1/roles/audit-logs/?module=auth&action=switch_branch', headers=headers)
    assert logs.status_code == 200
    payload = logs.json()
    # Should contain at least one log entry where user_id == admin.id
    if isinstance(payload, list):
        assert any(l.get('user_id') == admin.id for l in payload)
    else:
        # if wrapped
        data = payload.get('data') or []
        assert any(l.get('user_id') == admin.id for l in data)
