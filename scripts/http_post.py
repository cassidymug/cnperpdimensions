import json, sys, urllib.request
url = sys.argv[1]
body = json.loads(sys.argv[2])
req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
print(urllib.request.urlopen(req).read().decode())
