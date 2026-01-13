import requests
import json

# Load from environment variable - NEVER hardcode API keys!
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found in environment variables")
    exit(1)

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
