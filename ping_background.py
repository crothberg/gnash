import requests
import time

resp = requests.get('http://127.0.0.1:5000/longtask')
for i in range(15):
    print(requests.get(resp.headers['Location']).content)
    time.sleep(1)