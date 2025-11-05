import os
import sys
import time
import json
import requests

BASE_URL = os.environ.get('POS_BASE_URL', 'http://localhost:8010')
USERNAME = os.environ.get('POS_USER', 'superadmin')
PASSWORD = os.environ.get('POS_PASS', 'superadmin')
BRANCH_CODE = os.environ.get('POS_BRANCH', 'MAIN')


def fail(msg):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg):
    print(f"[OK] {msg}")


def main():
    print(f"POS smoke test against {BASE_URL}")

    # 1) Login
    login_url = f"{BASE_URL}/api/v1/auth/login-json"
    login_payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "branch_code": BRANCH_CODE
    }
    r = requests.post(login_url, json=login_payload)
    if r.status_code != 200:
        fail(f"Login failed: {r.status_code} {r.text}")
    tok = r.json()
    token = tok.get('access_token')
    if not token:
        fail("No access_token in login response")
    headers = { 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json' }
    ok("Logged in and obtained token")

    # Branch context
    branch_id = tok.get('branch_id')
    if not branch_id:
        print("[WARN] No branch_id from login; some endpoints may require it")

    # 2) Products
    prod_url = f"{BASE_URL}/api/v1/pos/products"
    params = {}
    if branch_id:
        params['branch_id'] = branch_id
    r = requests.get(prod_url, params=params, headers=headers)
    if r.status_code != 200:
        fail(f"Products list failed: {r.status_code} {r.text}")
    products = r.json()
    if isinstance(products, dict):
        products = products.get('data') or products.get('value') or []
    if not products:
        fail("No products returned — seed products before running smoke test")
    p = products[0]
    ok(f"Fetched {len(products)} products; using product: {p.get('name')} ({p.get('id')})")

    # 3) Customers
    cust_url = f"{BASE_URL}/api/v1/pos/customers"
    r = requests.get(cust_url, params=params, headers=headers)
    if r.status_code != 200:
        fail(f"Customers list failed: {r.status_code} {r.text}")
    customers = r.json().get('data', []) if isinstance(r.json(), dict) else r.json()
    cust_id = customers[0]['id'] if customers else None
    ok(f"Fetched {len(customers)} customers")

    # 4) Ensure/open POS session
    sessions_url = f"{BASE_URL}/api/v1/pos/sessions"
    r = requests.get(sessions_url, params={"status": "open", **({"branch_id": branch_id} if branch_id else {})}, headers=headers)
    if r.status_code == 200 and isinstance(r.json(), dict):
        open_sessions = r.json().get('data', [])
    else:
        open_sessions = []
    session_id = None
    if open_sessions:
        # Prefer session for this user if available
        user_id = tok.get('user', {}).get('id') or tok.get('user_id')
        mine = next((s for s in open_sessions if str(s.get('user_id')) == str(user_id)), None)
        session_id = mine.get('id') if mine else open_sessions[0].get('id')
        ok(f"Reusing open POS session: {session_id}")
    else:
        open_url = f"{BASE_URL}/api/v1/pos/sessions/open"
        payload = {
            "user_id": tok.get('user', {}).get('id') or tok.get('user_id'),
            "branch_id": branch_id,
            "till_id": f"SMOKE_{int(time.time())}",
            "float_amount": 0
        }
        r = requests.post(open_url, headers=headers, data=json.dumps(payload))
        if r.status_code != 200:
            fail(f"Open session failed: {r.status_code} {r.text}")
        session_id = r.json().get('data', {}).get('session_id')
        if not session_id:
            fail("No session_id returned when opening session")
        ok(f"Opened POS session: {session_id}")

    # 5) Post a small cash sale
    sales_url = f"{BASE_URL}/api/v1/pos/sales"
    # Compute tendered amount to cover VAT when applicable
    unit_price = float(p.get('selling_price') or 0)
    is_taxable = True if p.get('is_taxable', True) else False
    vat_rate = 14.0
    total_due = unit_price * (1.0 + (vat_rate / 100.0)) if is_taxable else unit_price
    # Add a tiny cushion to avoid float rounding causing "Insufficient payment"
    amount_tendered = round(total_due + 0.01, 2)

    sale_payload = {
        "session_id": session_id,
        "items": [
            {
                "product_id": p['id'],
                "quantity": 1,
                "unit_price": unit_price,
                "discount_amount": 0,
                "is_taxable": is_taxable
            }
        ],
        "customer_id": cust_id,  # Optional
        "payment_method": "cash",
        "amount_tendered": amount_tendered,
        "currency": tok.get('data', {}).get('currency', 'BWP') if isinstance(tok.get('data'), dict) else 'BWP',
        "vat_rate": vat_rate,
        "use_ifrs_posting": True
    }
    r = requests.post(sales_url, headers=headers, data=json.dumps(sale_payload))
    if r.status_code != 200:
        fail(f"Sale failed: {r.status_code} {r.text}")
    sj = r.json()
    if not sj.get('success'):
        fail(f"Sale response not success: {sj}")
    data = sj.get('data', {})
    ok(f"Sale posted. Reference: {data.get('reference') or data.get('sale_id')}")

    print("\nSmoke test PASSED.")


if __name__ == '__main__':
    main()
