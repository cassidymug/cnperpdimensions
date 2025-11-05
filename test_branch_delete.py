import requests

# Get all branches to find one to delete
r = requests.get('http://localhost:8010/api/v1/branches/statistics')
branches = r.json()

# Find the test branch we just updated
test_branch = [b for b in branches if b.get('name') == 'Updated Test Branch 4515']
if not test_branch:
    print('❌ Test branch not found')
    exit(1)

branch_id = test_branch[0]['id']
print('Deleting branch: ' + test_branch[0]['name'] + ' (' + branch_id + ')')

# Delete the branch with longer timeout
try:
    r = requests.delete('http://localhost:8010/api/v1/branches/' + branch_id, timeout=30)
    print('Status: ' + str(r.status_code))
    if r.status_code == 200:
        print('✅ Branch deleted successfully')

        # Verify it's gone
        r2 = requests.get('http://localhost:8010/api/v1/branches/statistics')
        remaining = len(r2.json())
        print('Remaining branches: ' + str(remaining))
    else:
        print('❌ Error: ' + r.text)
except Exception as e:
    print('❌ Timeout or error: ' + str(e))
