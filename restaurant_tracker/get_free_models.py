"""Fetch and filter free models from OpenRouter API"""
import requests
import json

def get_free_models():
    """Get all free models from OpenRouter API"""
    try:
        response = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        free_models = []
        
        if "data" in data:
            for model in data["data"]:
                model_id = model.get("id", "")
                pricing = model.get("pricing", {})
                
                # Check if model is free (both prompt and completion are 0 or None)
                prompt_price = pricing.get("prompt", "0")
                completion_price = pricing.get("completion", "0")
                
                # Convert to float for comparison
                try:
                    prompt_price = float(prompt_price) if prompt_price else 0
                    completion_price = float(completion_price) if completion_price else 0
                except (ValueError, TypeError):
                    prompt_price = 0
                    completion_price = 0
                
                # Also check if model ID ends with :free
                is_free = (prompt_price == 0 and completion_price == 0) or ":free" in model_id
                
                if is_free:
                    free_models.append({
                        "id": model_id,
                        "name": model.get("name", ""),
                        "context_length": model.get("context_length", 0),
                        "pricing": pricing
                    })
        
        # Sort by model ID
        free_models.sort(key=lambda x: x["id"])
        
        print(f"\nFound {len(free_models)} free models:\n")
        print("=" * 80)
        
        for model in free_models:
            print(f"ID: {model['id']}")
            print(f"Name: {model['name']}")
            print(f"Context Length: {model['context_length']}")
            print("-" * 80)
        
        # Save to file
        with open("free_models_list.json", "w", encoding="utf-8") as f:
            json.dump(free_models, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(free_models)} free models to free_models_list.json")
        
        # Print just the IDs for easy copy-paste
        print("\n" + "=" * 80)
        print("Model IDs (for script):")
        print("=" * 80)
        for model in free_models:
            print(f'        "{model["id"]}",')
        
        return free_models
        
    except Exception as e:
        print(f"Error fetching models: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    get_free_models()
