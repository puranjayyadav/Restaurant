import requests
import json

API_KEY = "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"

print("="*60)
print("Testing OpenRouter API")
print("="*60)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Simple test payload
payload = {
    "model": "mistralai/mistral-7b-instruct:free",
    "messages": [
        {"role": "user", "content": "Say 'Hello, OpenRouter is working!' and nothing else."}
    ],
    "max_tokens": 50
}

print(f"\nSending request to: https://openrouter.ai/api/v1/chat/completions")
print(f"Model: {payload['model']}")
print(f"API Key (first 20 chars): {API_KEY[:20]}...")
print("\nMaking request...")

try:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print(f"\nResponse Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✓ SUCCESS! Response:")
        print(json.dumps(result, indent=2))
        
        if "choices" in result:
            content = result["choices"][0]["message"]["content"]
            print(f"\n✓ Message: {content}")
    else:
        print(f"\n✗ ERROR! Status: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"\n✗ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
