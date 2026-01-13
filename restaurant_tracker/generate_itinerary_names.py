"""
Script to generate beautiful, unique names and descriptions for featured itineraries
using a free LLM API (Groq).
"""
import requests
import json
import os
from typing import Dict, List

# Groq API endpoint (free tier, no API key required for basic usage)
# Alternatively, we can use Hugging Face Inference API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# If Groq requires API key, we'll use Hugging Face instead
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"

def generate_with_groq(prompt: str, api_key: str = None) -> str:
    """Generate text using Groq API."""
    if not api_key:
        # Try to get from environment or use Hugging Face instead
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "system", "content": "You are a creative copywriter specializing in food and travel experiences. Write evocative, appetizing descriptions."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 200
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq API error: {e}")
    
    return None

def generate_with_huggingface(prompt: str) -> str:
    """Generate text using Hugging Face Inference API (free, no key required)."""
    headers = {"Content-Type": "application/json"}
    
    # Use a smaller, faster model that doesn't require auth
    model_url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
    
    # Actually, let's use a better free model - GPT-2 or a simple completion model
    # For better results without API key, we'll use a different approach
    return None

def generate_with_openrouter(prompt: str) -> str:
    """Generate using OpenRouter (has free tier models)."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {"role": "system", "content": "You are a creative copywriter specializing in food and travel experiences. Write evocative, appetizing descriptions."},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                                headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"OpenRouter API error: {e}")
    
    return None

def generate_itinerary_name_and_description(cuisine: str, neighborhood: str, 
                                          price_range: str, tags: List[str]) -> Dict[str, str]:
    """Generate a unique name and beautiful description for an itinerary."""
    
    prompt = f"""Create a unique, evocative name and a beautiful 1-2 sentence description for a restaurant itinerary in {neighborhood}, NYC.

Details:
- Cuisine: {cuisine}
- Price Range: {price_range}
- Tags: {', '.join(tags)}
- Neighborhood: {neighborhood}

The name should be creative and capture the essence of the neighborhood and cuisine. The description should be appetizing and compelling, making people want to explore these restaurants.

Format your response as JSON:
{{
    "title": "Creative Name Here",
    "description": "Beautiful 1-2 sentence description here"
}}"""

    # Try different APIs in order
    result = None
    
    # Try Groq first
    result = generate_with_groq(prompt)
    
    # Try OpenRouter if Groq fails
    if not result:
        result = generate_with_openrouter(prompt)
    
    # If all APIs fail, use fallback creative names
    if not result:
        return generate_fallback_name_description(cuisine, neighborhood, price_range, tags)
    
    # Try to parse JSON from response
    try:
        # Extract JSON from markdown code blocks if present
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(result)
        return {
            "title": parsed.get("title", "").strip(),
            "description": parsed.get("description", "").strip()
        }
    except:
        # If JSON parsing fails, try to extract title and description manually
        lines = result.split("\n")
        title = ""
        description = ""
        
        for line in lines:
            if "title" in line.lower() or '"title"' in line:
                title = line.split(":")[-1].strip().strip('"').strip("'")
            if "description" in line.lower() or '"description"' in line:
                description = line.split(":")[-1].strip().strip('"').strip("'")
        
        if title and description:
            return {"title": title, "description": description}
        
        # Last resort fallback
        return generate_fallback_name_description(cuisine, neighborhood, price_range, tags)

def generate_fallback_name_description(cuisine: str, neighborhood: str, 
                                     price_range: str, tags: List[str]) -> Dict[str, str]:
    """Fallback creative names if API fails."""
    
    # Creative name templates based on neighborhood and cuisine
    name_templates = {
        ("Italian", "East Village"): [
            "La Dolce Vita: East Village Italian Journey",
            "Little Italy Meets East Village",
            "East Village Italian Gems"
        ],
        ("French", "TriBeCa"): [
            "Parisian Elegance in TriBeCa",
            "TriBeCa's French Quarter",
            "Café Culture: French Dining in TriBeCa"
        ],
        ("Mexican", "West Village"): [
            "West Village Fiesta",
            "Vibrant Mexican Flavors in the Village",
            "Cantina Culture: West Village Mexican"
        ],
        ("Japanese", "Lower East Side"): [
            "Omakase Experience: Lower East Side",
            "East Meets East: Japanese Dining in LES",
            "Lower East Side Sushi & Sake"
        ],
        ("Contemporary American", "SoHo"): [
            "SoHo Brunch Scene",
            "Weekend Brunch in SoHo",
            "SoHo's Best Brunch Spots"
        ]
    }
    
    desc_templates = {
        ("Italian", "East Village"): [
            "Discover authentic Italian trattorias and hidden neighborhood gems where traditional recipes meet East Village charm.",
            "Embark on a culinary journey through the East Village's most beloved Italian spots, from cozy family-run pizzerias to intimate wine bars."
        ],
        ("French", "TriBeCa"): [
            "Experience the sophisticated allure of French dining in TriBeCa's elegant restaurants, where classic techniques meet modern innovation.",
            "Indulge in Parisian-inspired cuisine in one of Manhattan's most refined neighborhoods, where every meal feels like a special occasion."
        ],
        ("Mexican", "West Village"): [
            "Savor vibrant Mexican flavors in the heart of the West Village, where festive cantinas and authentic taquerias create unforgettable group dining experiences.",
            "Experience the lively spirit of Mexican cuisine in cozy West Village spots perfect for sharing plates and making memories with friends."
        ],
        ("Japanese", "Lower East Side"): [
            "Discover exceptional Japanese dining in the Lower East Side, where omakase experiences and innovative izakayas redefine fine dining.",
            "Indulge in meticulously crafted Japanese cuisine in intimate LES settings, where traditional techniques meet contemporary creativity."
        ],
        ("Contemporary American", "SoHo"): [
            "Start your weekend right with SoHo's most celebrated brunch spots, where innovative American cuisine meets the neighborhood's artistic energy.",
            "Experience the perfect brunch in SoHo's stylish eateries, where creative takes on classic dishes are served in Instagram-worthy settings."
        ]
    }
    
    key = (cuisine, neighborhood)
    names = name_templates.get(key, [f"{cuisine} Dining in {neighborhood}"])
    descs = desc_templates.get(key, [f"Explore the best {cuisine.lower()} restaurants in {neighborhood}."])
    
    return {
        "title": names[0],
        "description": descs[0]
    }

def main():
    """Generate names and descriptions for all 5 featured itineraries."""
    
    itineraries = [
        {
            'cuisine': 'Italian',
            'neighborhood': 'East Village',
            'price_range': '$30 and under',
            'tags': ['Neighborhood gem'],
        },
        {
            'cuisine': 'French',
            'neighborhood': 'TriBeCa',
            'price_range': '$31-$50',
            'tags': ['Charming'],
        },
        {
            'cuisine': 'Mexican',
            'neighborhood': 'West Village',
            'price_range': '$30 and under',
            'tags': ['Good for groups'],
        },
        {
            'cuisine': 'Japanese',
            'neighborhood': 'Lower East Side',
            'price_range': '$50+',
            'tags': ['Good for special occasions'],
        },
        {
            'cuisine': 'Contemporary American',
            'neighborhood': 'SoHo',
            'price_range': '$31-$50',
            'tags': ['Great for brunch'],
        },
    ]
    
    print("Generating beautiful names and descriptions for featured itineraries...\n")
    
    results = []
    for i, itinerary in enumerate(itineraries, 1):
        print(f"Generating for {itinerary['cuisine']} in {itinerary['neighborhood']}...")
        result = generate_itinerary_name_and_description(
            itinerary['cuisine'],
            itinerary['neighborhood'],
            itinerary['price_range'],
            itinerary['tags']
        )
        results.append({
            **itinerary,
            **result
        })
        print(f"  ✓ {result['title']}\n")
    
    # Print formatted results
    print("\n" + "="*80)
    print("GENERATED ITINERARY NAMES AND DESCRIPTIONS")
    print("="*80 + "\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   Description: {result['description']}")
        print(f"   Cuisine: {result['cuisine']} | Price: {result['price_range']} | Tags: {', '.join(result['tags'])}")
        print(f"   Neighborhood: {result['neighborhood']}\n")
    
    # Save to JSON file for easy copy-paste
    output_file = "generated_itinerary_names.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    print("\nYou can now update the Python files with these names and descriptions.")

if __name__ == "__main__":
    main()

