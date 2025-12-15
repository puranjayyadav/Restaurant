"""
Test the NBA API endpoint
"""

import requests
import json
from datetime import datetime

# Backend URL - adjust if needed
BASE_URL = "http://localhost:8000"

def test_nba_endpoint():
    """Test the Next Best Action endpoint"""
    print("=" * 60)
    print("Testing NBA API Endpoint")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/next-best-action/"
    
    # Test data (Soho, NYC)
    payload = {
        "latitude": 40.7231,
        "longitude": -73.9969,
        "heading": 0.0,  # North
        "timestamp": datetime.now().isoformat() + "Z"
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))
            
            if result.get('cache_hit'):
                print("\n[OK] Cache hit - fast response!")
            else:
                print("\n[INFO] Cache miss - this is expected if no data cached yet")
            
            if result.get('next_stop'):
                print(f"\n[OK] Next Stop: {result['next_stop']['name']}")
                print(f"  Distance: {result['next_stop']['distance_m']}m")
                print(f"  Bearing: {result['next_stop']['bearing']}")
                print(f"  ETA: {result['next_stop']['estimated_arrival']}")
        else:
            print(f"\n[ERROR] Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Connection Error: Is the Django server running?")
        print("  Start it with: cd my_new_project && python manage.py runserver")
    except Exception as e:
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    test_nba_endpoint()

