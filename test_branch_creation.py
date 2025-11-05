import requests
import random

branch_data = {
    'name': f'Test Branch {random.randint(1000, 9999)}',
    'code': f'TB{random.randint(1000, 9999)}',
    'location': 'Test Loc',
    'phone': '555-1234',
    'email': 'test@example.com',
    'address': '123 St',
    'is_head_office': False,
    'manager_id': None,
    'contact_person': 'John',
    'fax': '555-5678',
    'website': 'https://test.com',
    'timezone': 'UTC',
    'currency': 'USD',
    'active': True,
    'notes': 'Test'
}

try:
    r = requests.post('http://localhost:8010/api/v1/branches', json=branch_data, timeout=5)
    print('Status: ' + str(r.status_code))
    if r.status_code == 200:
        name = r.json().get('name')
        print('✅ Created: ' + name)
    else:
        print('❌ Error: ' + r.text)
except Exception as e:
    print('❌ Exception: ' + str(e))
