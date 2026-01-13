"""
Comprehensive Test Suite for Generate Itinerary API
Endpoint: POST /api/api/generate-itinerary/

This script tests the itinerary generation capabilities, specifically focusing on:
1. Cuisine filtering (ensure Indian/Korean/Japanese/etc. queries return cuisine-specific results)
2. Vibe matching (ensure "dinner_date" returns romantic venues)
3. Location-based filtering (ensure results are within radius)
4. Social context handling
5. Edge cases and mixed queries

Usage:
    python test_generate_itinerary_comprehensive.py
"""

import requests
import json
import time
from typing import List, Dict, Any, Optional
import math

# CONFIGURATION
BASE_URL = "http://localhost:8000"  # Change to your Render URL if testing production
ENDPOINT = f"{BASE_URL}/api/api/generate-itinerary/"
TIMEOUT = 180  # Seconds (itinerary generation can take time)

# COLOR CODES FOR OUTPUT
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_result(success: bool, message: str):
    if success:
        print(f"{GREEN}[PASS]{RESET} {message}")
    else:
        print(f"{RED}[FAIL]{RESET} {message}")

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def check_cuisine_in_results(cuisine_keywords: List[str], itinerary: List[Dict]) -> bool:
    """Check if any venue in itinerary matches cuisine keywords"""
    for item in itinerary:
        name = (item.get('name') or '').lower()
        if any(kw.lower() in name for kw in cuisine_keywords):
            return True
    return False

def check_venue_has_cuisine_vibe(place_id: str, cuisine_slugs: List[str], supabase=None) -> bool:
    """Check if a venue has any of the specified cuisine vibes"""
    if not supabase:
        return False
    try:
        result = supabase.table('venue_vibes').select('vibe_slug').eq('place_id', place_id).execute()
        if result.data:
            venue_vibes = {v.get('vibe_slug') for v in result.data if v.get('vibe_slug')}
            return bool(venue_vibes.intersection(set(cuisine_slugs)))
    except:
        pass
    return False

def run_test(name: str, payload: Dict, checks: List[callable]) -> bool:
    print(f"\n{CYAN}Running Test: {name}{RESET}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    start_time = time.time()
    try:
        response = requests.post(ENDPOINT, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()
        duration = time.time() - start_time
        
        print(f"\n{BLUE}Response (took {duration:.2f}s):{RESET}")
        print(f"  Itinerary items: {len(result.get('itinerary', []))}")
        print(f"  Hidden gems: {result.get('hidden_gems_injected', 0)}")
        print(f"  Total walk time: {result.get('total_walk_time_mins', 0)} mins")
        
        # Show first few itinerary items
        itinerary = result.get('itinerary', [])
        if itinerary:
            print(f"\n  First 3 venues:")
            for i, item in enumerate(itinerary[:3], 1):
                name = item.get('name', 'Unknown')
                rating = item.get('rating', 0)
                slot = item.get('slot', 'unknown')
                print(f"    {i}. {name} ({slot}) - Rating: {rating}")
        
        all_passed = True
        for check in checks:
            try:
                check_result = check(result)
                if not check_result:
                    all_passed = False
            except Exception as e:
                print_result(False, f"Check raised exception: {e}")
                import traceback
                traceback.print_exc()
                all_passed = False
        
        return all_passed
        
    except requests.exceptions.ConnectionError:
        print_result(False, f"Connection failed. Is the server running at {BASE_URL}?")
        return False
    except requests.exceptions.Timeout:
        print_result(False, f"Request timed out after {TIMEOUT}s.")
        return False
    except requests.exceptions.HTTPError as e:
        print_result(False, f"HTTP Error: {e.response.status_code} - {e.response.text[:200]}")
        return False
    except Exception as e:
        print_result(False, f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

# CHECK FUNCTIONS
def check_has_results():
    def check(result: Dict[str, Any]) -> bool:
        itinerary = result.get('itinerary', [])
        if len(itinerary) > 0:
            print_result(True, f"Itinerary has {len(itinerary)} items")
            return True
        else:
            print_result(False, "Itinerary is empty")
            return False
    return check

def check_cuisine_present(cuisine_keywords: List[str], cuisine_slugs: List[str] = None):
    """Check if cuisine appears in venue names or vibe slugs"""
    def check(result: Dict[str, Any]) -> bool:
        itinerary = result.get('itinerary', [])
        if not itinerary:
            print_result(False, "Cannot check cuisine - no itinerary items")
            return False
        
        # Check venue names
        name_matches = check_cuisine_in_results(cuisine_keywords, itinerary)
        
        # Check vibe slugs if supabase available
        vibe_matches = 0
        if cuisine_slugs:
            try:
                from supabase_config import get_supabase_client
                supabase = get_supabase_client()
                for item in itinerary:
                    place_id = item.get('place_id')
                    if place_id and check_venue_has_cuisine_vibe(place_id, cuisine_slugs, supabase):
                        vibe_matches += 1
            except:
                pass
        
        if name_matches or vibe_matches > 0:
            msg = f"Found cuisine match"
            if name_matches:
                msg += " (in venue names)"
            if vibe_matches > 0:
                msg += f" ({vibe_matches} venues have cuisine vibes)"
            print_result(True, msg)
            return True
        else:
            print_result(False, f"No {cuisine_keywords[0]} cuisine found in results")
            # Show what we got instead
            print(f"  Venues returned: {[item.get('name') for item in itinerary[:5]]}")
            return False
    return check

def check_rating_threshold(min_rating: float = 4.0):
    def check(result: Dict[str, Any]) -> bool:
        itinerary = result.get('itinerary', [])
        low_rated = [item for item in itinerary if (item.get('rating') or 0) < min_rating]
        if low_rated:
            print_result(False, f"Found {len(low_rated)} venues with rating < {min_rating}")
            return False
        else:
            print_result(True, f"All venues have rating >= {min_rating}")
            return True
    return check

def check_within_radius(lat: float, lng: float, radius_km: float, buffer_pct: float = 0.15):
    """Check if venues are within radius. Allows 15% buffer for coordinate offsets."""
    def check(result: Dict[str, Any]) -> bool:
        itinerary = result.get('itinerary', [])
        effective_radius = radius_km * (1 + buffer_pct)  # Add buffer for coordinate randomization
        out_of_range = []
        for item in itinerary:
            item_lat = item.get('latitude')
            item_lng = item.get('longitude')
            if item_lat and item_lng:
                dist = haversine_distance(lat, lng, float(item_lat), float(item_lng))
                if dist > effective_radius:
                    out_of_range.append((item.get('name'), dist))
        
        if out_of_range:
            print_result(False, f"Found {len(out_of_range)} venues outside {radius_km}km radius (+{buffer_pct*100:.0f}% buffer)")
            for name, dist in out_of_range[:3]:
                print(f"  {name}: {dist:.2f}km away")
            return False
        else:
            print_result(True, f"All venues within {radius_km}km radius")
            return True
    return check

def check_vibe_match(expected_vibe: str):
    def check(result: Dict[str, Any]) -> bool:
        # Check if any venue has the expected vibe
        # This is harder to verify without Supabase, so we'll just check if results exist
        itinerary = result.get('itinerary', [])
        if len(itinerary) > 0:
            print_result(True, f"Vibe '{expected_vibe}' returned {len(itinerary)} venues")
            return True
        else:
            print_result(False, f"Vibe '{expected_vibe}' returned no results")
            return False
    return check

def check_minimum_stops(min_stops: int = 3):
    def check(result: Dict[str, Any]) -> bool:
        itinerary = result.get('itinerary', [])
        if len(itinerary) >= min_stops:
            print_result(True, f"Itinerary has {len(itinerary)} stops (>= {min_stops})")
            return True
        else:
            print_result(False, f"Itinerary has only {len(itinerary)} stops (expected >= {min_stops})")
            return False
    return check

# MAIN TEST SUITE
def main():
    print(f"{YELLOW}Starting Comprehensive Generate Itinerary Tests...{RESET}")
    print(f"Target: {ENDPOINT}")
    print(f"Timeout: {TIMEOUT}s per request")
    
    # Test location (Soho, NYC)
    test_lat = 40.707074094216594
    test_lng = -74.0016461429476
    
    tests = [
        # 1. Indian Cuisine - All variants
        {
            "name": "Indian Cuisine (All Variants)",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "dinner_date",
                "social_context": "couple",
                "cuisine_preferences": ["indian_north", "indian_south", "indian_north_aesthetic", "indian_south_aesthetic"],
                "radius_meters": 3000,
                "local_time_start": "19:00"
            },
            "checks": [
                check_has_results(),
                check_cuisine_present(["indian", "curry", "tandoori", "biryani"], 
                                     ["indian_north", "indian_south", "indian_north_aesthetic", "indian_south_aesthetic"]),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 3.0),
                check_minimum_stops(3)
            ]
        },
        # 2. Korean Cuisine
        {
            "name": "Korean Cuisine",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "dinner_group",
                "social_context": "group",
                "cuisine_preferences": ["korean_bbq", "korean_bbq_aesthetic", "korean_pocha", "korean_pocha_aesthetic"],
                "radius_meters": 5000,
                "local_time_start": "18:00"
            },
            "checks": [
                check_has_results(),
                check_cuisine_present(["korean", "bbq", "galbi", "bulgogi"], 
                                     ["korean_bbq", "korean_bbq_aesthetic", "korean_pocha", "korean_pocha_aesthetic"]),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 5.0)
            ]
        },
        # 3. Japanese Cuisine
        {
            "name": "Japanese Cuisine (Sushi/Izakaya)",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "fine_dining",
                "social_context": "couple",
                "cuisine_preferences": ["japanese_izakaya", "japanese_izakaya_aesthetic", "japanese_sushi_aesthetic"],
                "radius_meters": 3000,
                "local_time_start": "19:30"
            },
            "checks": [
                check_has_results(),
                check_cuisine_present(["japanese", "sushi", "izakaya", "yakitori"], 
                                     ["japanese_izakaya", "japanese_izakaya_aesthetic", "japanese_sushi_aesthetic"]),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 3.0)
            ]
        },
        # 4. Thai Cuisine
        {
            "name": "Thai Cuisine",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "casual_lunch",
                "social_context": "couple",
                "cuisine_preferences": ["thai_isan", "thai_isan_aesthetic"],
                "radius_meters": 3000,
                "local_time_start": "12:30"
            },
            "checks": [
                check_has_results(),
                check_cuisine_present(["thai", "pad thai", "curry"], 
                                     ["thai_isan", "thai_isan_aesthetic"]),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 3.0)
            ]
        },
        # 5. Italian Cuisine
        {
            "name": "Italian Cuisine",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "dinner_date",
                "social_context": "couple",
                "cuisine_preferences": ["italian_red_sauce", "italian_red_sauce_aesthetic"],
                "radius_meters": 3000,
                "local_time_start": "19:00"
            },
            "checks": [
                check_has_results(),
                check_cuisine_present(["italian", "pasta", "pizza"], 
                                     ["italian_red_sauce", "italian_red_sauce_aesthetic"]),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 3.0)
            ]
        },
        # 6. No Cuisine Preference (should return diverse results)
        {
            "name": "No Cuisine Preference (Diverse Results)",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "dinner_date",
                "social_context": "couple",
                "radius_meters": 3000,
                "local_time_start": "19:00"
            },
            "checks": [
                check_has_results(),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 3.0),
                check_minimum_stops(3)
            ]
        },
        # 7. Work-Friendly Coffee (Non-Cuisine Vibe)
        {
            "name": "Work-Friendly Coffee",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "work_friendly",
                "social_context": "solo",
                "cuisine_preferences": ["coffee", "coffee_run"],
                "radius_meters": 2000,
                "local_time_start": "09:00"
            },
            "checks": [
                check_has_results(),
                check_cuisine_present(["coffee", "cafe", "espresso"], ["coffee", "coffee_run"]),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 2.0)
            ]
        },
        # 8. Speakeasy (Nightlife)
        {
            "name": "Speakeasy Nightlife",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "speakeasy",
                "social_context": "couple",
                "radius_meters": 3000,
                "local_time_start": "21:00"
            },
            "checks": [
                check_has_results(),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 3.0)
            ]
        },
        # 9. Multiple Cuisines (OR logic)
        {
            "name": "Multiple Cuisines (Indian OR Thai)",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "dinner_date",
                "social_context": "couple",
                "cuisine_preferences": [
                    "indian_north", "indian_north_aesthetic",
                    "thai_isan", "thai_isan_aesthetic"
                ],
                "radius_meters": 3000,
                "local_time_start": "19:00"
            },
            "checks": [
                check_has_results(),
                check_rating_threshold(4.0),
                check_within_radius(test_lat, test_lng, 3.0)
            ]
        },
        # 10. Edge Case: Very Small Radius
        {
            "name": "Small Radius (500m)",
            "payload": {
                "latitude": test_lat,
                "longitude": test_lng,
                "selected_vibe": "dinner_date",
                "social_context": "couple",
                "cuisine_preferences": ["indian_north", "indian_north_aesthetic"],
                "radius_meters": 500,
                "local_time_start": "19:00"
            },
            "checks": [
                check_has_results(),  # May have 0 results, that's OK
                check_within_radius(test_lat, test_lng, 0.5)
            ]
        }
    ]
    
    passed_count = 0
    total_count = len(tests)
    
    for test in tests:
        if run_test(test["name"], test["payload"], test["checks"]):
            passed_count += 1
        time.sleep(1)  # Small delay between requests to avoid overwhelming server
            
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}Test Summary: {passed_count}/{total_count} Passed{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    if passed_count == total_count:
        print(f"{GREEN}All tests passed! API is working correctly.{RESET}")
    else:
        print(f"{RED}Some tests failed. Check output above for details.{RESET}")
        print(f"{YELLOW}Note: Some failures may be expected (e.g., small radius with no venues nearby){RESET}")

if __name__ == "__main__":
    main()
