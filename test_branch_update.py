import requests

# Get all branches to find one to edit
r = requests.get('http://localhost:8010/api/v1/branches/statistics')
branches = r.json()

# Find the test branch we just created
test_branch = [b for b in branches if b.get('name').startswith('Test Branch 4515')]
if not test_branch:
    print('❌ Test branch not found')
    exit(1)

branch_id = test_branch[0]['id']
print('Editing branch: ' + test_branch[0]['name'] + ' (' + branch_id + ')')

# Update the branch
update_data = {
    'name': 'Updated Test Branch 4515',
    'location': 'Updated Location',
    'phone': '555-9999',
    'email': 'updated@example.com',
    'address': '456 Updated St',
    'contact_person': 'Jane Doe',
    'fax': '555-0000',
    'website': 'https://updated.com',
    'timezone': 'UTC',
    'currency': 'USD',
    'active': True,
    'notes': 'Updated test branch'
}

r = requests.put('http://localhost:8010/api/v1/branches/' + branch_id, json=update_data, timeout=5)
print('Status: ' + str(r.status_code))
if r.status_code == 200:
    updated = r.json()
    print('✅ Updated: ' + updated.get('name'))
    print('   Location: ' + updated.get('location'))
    print('   Phone: ' + updated.get('phone'))
else:
    print('❌ Error: ' + r.text)
