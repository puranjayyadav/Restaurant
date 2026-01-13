
import requests
import json
import time

def test_generate_itinerary(query, lat=None, lng=None):
    url = "http://localhost:8000/api/generate-itinerary/"
    payload = {
        "query": query,
        "k": 10
    }
    if lat and lng:
        payload["start_lat"] = lat
        payload["start_long"] = lng
        
    print(f"\n🚀 TESTING: '{query}' (Location: {lat}, {lng})")
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        duration = time.time() - start_time
        
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            itinerary = data.get('itinerary', [])
            detected_vibe = data.get('detected_vibe')
            
            print(f"✅ Found {len(itinerary)} results")
            print(f"🎭 Detected Vibe: {detected_vibe}")
            
            # Print breakdown
            sources = {}
            for item in itinerary:
                src = "lemon8" if item.get('is_lemon8') else ("gem" if item.get('is_gem') else "venue")
                sources[src] = sources.get(src, 0) + 1
            
            print(f"🧱 Source Breakdown: {sources}")
            
            if itinerary:
                print(f"📍 Sample: {itinerary[0].get('name')} ({itinerary[0].get('category')})")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: The server took too long to respond.")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")

if __name__ == "__main__":
    print("--- STARTING API STRESS TEST ---")
    
    # Test 1: Vibe detection (Work Friendly)
    test_generate_itinerary("work friendly cafes")
    
    # Test 2: Neighborhood detection (SoHo)
    test_generate_itinerary("brunch in SoHo", 40.7233, -74.0030)
    
    # Test 3: Specific cuisine
    test_generate_itinerary("Indian food in Manhattan", 40.7831, -73.9712)
    
    # Test 4: Hidden Gem check (Casual)
    test_generate_itinerary("casual lunch")
    
    # Test 5: Broad query (Diversity check)
    test_generate_itinerary("new spots")
    
    print("\n--- TEST COMPLETE ---")
