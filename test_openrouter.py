"""Test OpenRouter API with example data"""
import json
import sys
import requests

# API Key
OPENROUTER_API_KEY = "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"

# Example HTML content (simplified)
example_html = """<section id="article-content">
<h1 class="wap-article-title">Where to eat in NEW YORK CITY! 🍴🍎🗽</h1>
<div class="article-content-v2">
<article>
<p>During my most recent trip to <a class="l8editor-poi" data-discover="true" href="/poi/22535865201205278?region=us"><i></i><span>New York</span></a> we tried a few new places along with some tried and trued! Here's some recommendations on where to eat or grab coffee in New York City!</p>
<p><a class="l8editor-poi" data-discover="true" href="/poi/22535865249280777?region=us"><i></i><span>Thai Diner</span></a> is a Michelin rated Thai restaurant with great food, decent prices and an awesome vibe.</p>
<p>Check out <a class="l8editor-poi" data-discover="true" href="/poi/22535865249144220?region=us"><i></i><span>Panorama Room</span></a> on Roosevelt Island for great city views and good drinks (pro tip: take the Roosevelt Island tram to get there for some more sightseeing!)</p>
<p><a class="l8editor-poi" data-discover="true" href="/poi/22535934011453059?region=us"><i></i><span>Leon's Bagels</span></a> in Brooklyn is a cute little walk up bagel shop where you can get a pretty tasty bagel and a coffee.</p>
</article>
</div>
</section>"""

EXTRACTION_PROMPT = """You are a precision Data Extraction Agent. Your job is to convert raw HTML content from social media posts into structured JSON itineraries.

RULES:

1. INPUT: You will receive raw HTML content from a Lemon8 post.

2. TARGET: Extract every location/restaurant mentioned.

3. PRIORITY: Look for text inside <a class="l8editor-poi"> tags — these are the official Place Names. If not present, infer names from the text (e.g., "1. Katz's Deli").

4. CONTEXT: Extract specific recommendations (what to order, vibe, tips) from the surrounding <p> tags.

5. SEARCH QUERY: You MUST generate a 'search_query' field for each stop. Format: "{Place Name} {Neighborhood} {City}". If City is unknown, default to "New York".

6. OUTPUT: Return ONLY valid JSON. Do not include markdown formatting (```json), explanations, or conversational filler.

JSON SCHEMA:

{
  "itinerary_title": "String (Infer from <h1> or content)",
  "city": "String (e.g., New York, Brooklyn)",
  "stops": [
    {
      "place_name": "String (Official name)",
      "search_query": "String (Optimized for Google Maps)",
      "category": "String (e.g., Food, Activity, Coffee, Nightlife)",
      "notes": "String (Summary of what the creator said about this spot)"
    }
  ]
}"""

def test_openrouter():
    """Test OpenRouter API with example data"""
    print("Testing OpenRouter API...")
    sys.stdout.flush()
    print(f"API Key: {OPENROUTER_API_KEY[:20]}...")
    sys.stdout.flush()
    print()
    sys.stdout.flush()
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "Lemon8 Itinerary Extractor"
    }
    
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"Extract itinerary data from this HTML content:\n\n{example_html}"}
        ],
        "temperature": 0.1,
        "max_tokens": 2000
    }
    
    print("Sending request to OpenRouter...")
    print(f"Model: {payload['model']}")
    print(f"HTML content length: {len(example_html)} characters")
    print()
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Success! Response received:")
            print(json.dumps(result, indent=2))
            
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"].strip()
                print(f"\n✓ Extracted content ({len(content)} characters):")
                print(content)
                return True
            else:
                print("\n⚠ Response doesn't contain 'choices' field")
                print(f"Response keys: {list(result.keys())}")
                return False
        else:
            print(f"✗ Error! Status code: {response.status_code}")
            print(f"Response text: {response.text}")
            
            try:
                error_json = response.json()
                print(f"Error JSON: {json.dumps(error_json, indent=2)}")
            except:
                pass
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Request timed out after 60 seconds")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("OpenRouter API Test")
    print("="*60)
    print()
    
    success = test_openrouter()
    
    print()
    print("="*60)
    if success:
        print("✓ Test PASSED - OpenRouter is working!")
    else:
        print("✗ Test FAILED - Check the error messages above")
    print("="*60)
