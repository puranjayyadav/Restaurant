import requests
import json

url = "http://127.0.0.1:8005/api/lemon8/semantic-search/"
payload = {"query": "romantic date in soho", "k": 1}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
