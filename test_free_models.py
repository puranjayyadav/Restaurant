"""Test which free models actually work on OpenRouter"""
import requests
import json
import time

API_KEY = "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"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com",
    "X-Title": "Model Tester"
}

# Models to test
models_to_test = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "deepseek/deepseek-r1:free",
    "deepseek/deepseek-v3-0324:free",
    "google/gemini-2.0-flash-exp:free",
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-120b:free",
    "mistralai/mistral-7b-instruct:free",
    # Try some variations
    "meta-llama/llama-3-8b-instruct:free",
    "google/gemini-2.5-pro-exp-03-25:free",
]

print("Testing free models on OpenRouter...")
print("="*60)

working_models = []
failed_models = []

for model in models_to_test:
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Say 'test' and nothing else."}
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                if content and content.strip():
                    print(f"✓ {model} - WORKS (returned: {content.strip()[:50]})")
                    working_models.append(model)
                else:
                    print(f"⚠ {model} - 200 OK but empty content")
                    failed_models.append((model, "empty_content"))
            else:
                print(f"✗ {model} - 200 OK but no choices")
                failed_models.append((model, "no_choices"))
        elif response.status_code == 404:
            print(f"✗ {model} - 404 (model not found)")
            failed_models.append((model, "404"))
        elif response.status_code == 429:
            print(f"⚠ {model} - 429 (rate limited, but exists)")
            working_models.append(model)  # It exists, just rate limited
        elif response.status_code == 402:
            print(f"✗ {model} - 402 (requires payment)")
            failed_models.append((model, "402"))
        else:
            error_text = response.text[:200]
            print(f"✗ {model} - {response.status_code} ({error_text})")
            failed_models.append((model, f"{response.status_code}"))
        
        time.sleep(1)  # Rate limit protection
        
    except Exception as e:
        print(f"✗ {model} - Exception: {e}")
        failed_models.append((model, str(e)))
        time.sleep(1)

print("\n" + "="*60)
print("SUMMARY:")
print("="*60)
print(f"\n✓ Working models ({len(working_models)}):")
for model in working_models:
    print(f"  - {model}")

print(f"\n✗ Failed models ({len(failed_models)}):")
for model, reason in failed_models:
    print(f"  - {model} ({reason})")

print("\n" + "="*60)
print("Copy-paste ready list:")
print("="*60)
print("models_to_try = [")
for model in working_models:
    print(f'    "{model}",')
print("]")
