import requests
import json

API_KEY = "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"

print("Testing OpenRouter...")
print(f"API Key: {API_KEY[:30]}...")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com",
    "X-Title": "Test"
}

payload = {
    "model": "mistralai/mistral-7b-instruct:free",
    "messages": [
        {"role": "user", "content": "Say 'test successful' and nothing else."}
    ],
    "max_tokens": 20
}

print("\nSending request...")
response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers=headers,
    data=json.dumps(payload),
    timeout=30
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text[:500]}")

if response.status_code == 200:
    result = response.json()
    print(f"\nSuccess! Content: {result.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')}")
else:
    print(f"\nError: {response.text}")
