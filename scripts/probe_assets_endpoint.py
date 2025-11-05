import urllib.request, urllib.error

url = 'http://localhost:8010/api/v1/asset-management/assets/'
req = urllib.request.Request(url)
try:
    with urllib.request.urlopen(req) as r:
        print('STATUS', r.status)
        body = r.read().decode('utf-8', errors='replace')
        print(body[:4000])
except urllib.error.HTTPError as e:
    print('STATUS', e.code)
    body = e.read().decode('utf-8', errors='replace')
    print(body[:4000])
except Exception as e:
    print('ERR', repr(e))
