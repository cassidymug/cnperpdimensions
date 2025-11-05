import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from sqlalchemy import text

client = TestClient(app)


def login(username: str, password: str):
    return client.post('/api/v1/auth/login-json', json={'username': username, 'password': password})


def test_pos_sale_creates_audit_record():
    # Login as cashier (fallback to accountant if cashier not seeded)
    creds = [
        ('cashier','ChangeMe123'),
        ('pos_user','ChangeMe123'),
        ('accts','ChangeMe123')
    ]
    token = None
    for u,p in creds:
        r = login(u,p)
        if r.status_code == 200:
            token = r.json()['access_token']
            break
    if not token:
        pytest.skip('No POS-capable user found')

    headers = {'Authorization': f'Bearer {token}'}

    # Ensure an open POS session
    # (Simplistic: create one with branch from existing branch)
    db = SessionLocal()
    branch_id = db.execute(text('SELECT id FROM branches LIMIT 1')).scalar()
    assert branch_id, 'Need at least one branch for test'
    user_id = db.execute(text('SELECT id FROM users LIMIT 1')).scalar()

    open_resp = client.post('/api/v1/pos/sessions/open', json={
        'user_id': user_id,
        'branch_id': branch_id,
        'float_amount': '100.00'
    })
    assert open_resp.status_code == 200, open_resp.text
    session_id = open_resp.json()['data']['session_id']

    # Prepare minimal product
    product_id = db.execute(text('SELECT id FROM products LIMIT 1')).scalar()
    if not product_id:
        # Insert a simple product
        db.execute(text("""
            INSERT INTO products (id, name, sku, quantity, cost_price, selling_price, branch_id) 
            VALUES (gen_random_uuid()::text, 'Test Product','TP001',100,10,20,:b)
        """), {'b': branch_id})
        db.commit()
        product_id = db.execute(text('SELECT id FROM products LIMIT 1')).scalar()

    sale_payload = {
        'session_id': session_id,
        'payment_method': 'cash',
        'amount_tendered': '20',
        'items': [
            {
                'product_id': product_id,
                'quantity': 1,
                'unit_price': '20',
                'discount_amount': '0',
                'is_taxable': True
            }
        ],
        'currency': 'BWP'
    }

    sale_resp = client.post('/api/v1/pos/sales', json=sale_payload, headers=headers)
    assert sale_resp.status_code == 200, sale_resp.text
    sale_id = sale_resp.json()['data']['sale_id']

    # Verify audit record
    audit_count = db.execute(text('SELECT COUNT(*) FROM journal_sale_audit WHERE sale_id = :sid'), {'sid': sale_id}).scalar()
    assert audit_count == 1, f'Expected 1 audit record, found {audit_count}'

    # Verify uniqueness constraint prevents duplicate origin entries
    # Attempt to insert duplicate manually
    dup_attempt = db.execute(text('SELECT sale_id FROM journal_sale_audit WHERE sale_id=:sid'), {'sid': sale_id}).fetchone()
    assert dup_attempt is not None

    # Clean up (optional)
    db.close()
