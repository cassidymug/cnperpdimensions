import requests

# Update via the /api/v1/app-settings/ endpoint (what the frontend uses)
update_data = {
    'company_name': 'My Custom Company',
    'app_name': 'Custom ERP',
    'email': 'support@custom.com',
    'phone': '+267-311-5000',
    'website': 'https://custom.com',
    'address': '789 Custom Street'
}

try:
    r = requests.put('http://localhost:8010/api/v1/app-settings/', json=update_data)
    print('UPDATE Status: ' + str(r.status_code))

    # Now fetch via the settings endpoint to verify persistence
    r2 = requests.get('http://localhost:8010/api/v1/settings/')
    data = r2.json()

    if 'data' in data and 'business' in data['data']:
        b = data['data']['business']
        print('\n✅ Settings persisted to database:')
        print('  Company: ' + b.get('company_name'))
        print('  Email: ' + b.get('email'))
        print('  Phone: ' + b.get('phone'))
        print('  Website: ' + b.get('website'))
    else:
        print('Error reading settings')
except Exception as e:
    print('Error: ' + str(e))
