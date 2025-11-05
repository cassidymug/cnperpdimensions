import requests

r = requests.get('http://localhost:8010/api/v1/branches/statistics')
branches = r.json()
print('Total branches: ' + str(len(branches)))
print('Last 3 branches:')
for b in branches[-3:]:
    print('  - ' + b.get('name') + ' (' + b.get('code') + ')')
