import requests
import json

# Update business settings - with FLAT structure
settings_update = {
    'company_name': 'ACME Corporation',
    'app_name': 'ACME ERP System',
    'phone': '+267-555-0100',
    'email': 'info@acme.com',
    'website': 'https://www.acme.com',
    'address': '456 Business Avenue, Gaborone, Botswana'
}

try:
    # Update via API
    r = requests.put('http://localhost:8010/api/v1/settings/', json=settings_update, timeout=5)
    print('Status: ' + str(r.status_code))

    if r.status_code in [200, 201]:
        print('✅ Settings updated successfully')

        # Now verify by fetching
        r2 = requests.get('http://localhost:8010/api/v1/settings/', timeout=5)
        data = r2.json()
        if 'data' in data and 'business' in data['data']:
            business = data['data']['business']
            print('Updated values:')
            print('  Company Name: ' + str(business.get('company_name')))
            print('  Email: ' + str(business.get('email')))
            print('  Phone: ' + str(business.get('phone')))
    else:
        print('❌ Error updating settings: ' + str(r.status_code))
        print('Response: ' + r.text)

except Exception as e:
    print('❌ Exception: ' + str(e))
