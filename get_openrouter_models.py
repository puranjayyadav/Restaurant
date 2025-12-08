"""Fetch the actual list of free models from OpenRouter API"""
import requests
import json

API_KEY = "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"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print("Fetching models from OpenRouter API...")
print("="*60)

try:
    # Get models list from OpenRouter (may not require auth)
    response = requests.get(
        "https://openrouter.ai/api/v1/models",
        timeout=30
    )
    
    if response.status_code == 200:
        models_data = response.json()
        
        # Filter for free models
        free_models = []
        for model in models_data.get("data", []):
            model_id = model.get("id", "")
            if ":free" in model_id:
                free_models.append({
                    "id": model_id,
                    "name": model.get("name", ""),
                    "context_length": model.get("context_length", 0),
                    "pricing": model.get("pricing", {})
                })
        
        print(f"\nFound {len(free_models)} free models:\n")
        for model in sorted(free_models, key=lambda x: x["id"]):
            print(f"  {model['id']}")
            if model.get("name"):
                print(f"    Name: {model['name']}")
            if model.get("context_length"):
                print(f"    Context: {model['context_length']}")
            print()
        
        # Save to file
        with open("openrouter_free_models.json", "w", encoding="utf-8") as f:
            json.dump(free_models, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved to openrouter_free_models.json")
        
        # Print just the IDs for easy copy-paste
        print("\n" + "="*60)
        print("Model IDs (for copy-paste):")
        print("="*60)
        for model in sorted(free_models, key=lambda x: x["id"]):
            print(f'        "{model["id"]}",')
            
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
