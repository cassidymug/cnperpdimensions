import requests

try:
    r = requests.get('http://localhost:8010/api/v1/settings/', timeout=5)
    print('Status: ' + str(r.status_code))
    data = r.json()

    if 'data' in data and 'business' in data['data']:
        business = data['data']['business']
        print('Business Settings from API:')
        print('  Company Name: ' + str(business.get('company_name', 'N/A')))
        print('  App Name: ' + str(business.get('app_name', 'N/A')))
        print('  Email: ' + str(business.get('email', 'N/A')))
        print('  Phone: ' + str(business.get('phone', 'N/A')))
        print('  Address: ' + str(business.get('address', 'N/A')))
    else:
        print('No business settings in response')
        print('Response keys: ' + str(list(data.keys())))
except Exception as e:
    print('❌ Exception: ' + str(e))
