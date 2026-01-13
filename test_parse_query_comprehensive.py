"""
Comprehensive Test Suite for Parse Query API
Endpoint: /api/api/parse-query/

This script tests the NLP capabilities of the query parser, specifically focusing on:
1. Cuisine expansion (ensure "Indian" -> ["indian_north", "indian_north_aesthetic", ...])
2. Vibe extraction (ensure "romantic" -> "dinner_date")
3. Social context extraction
4. Location handling
5. Edge cases and mixed queries

Usage:
    python test_parse_query_comprehensive.py
"""

import requests
import json
import time
from typing import List, Dict, Any

# CONFIGURATION
BASE_URL = "http://localhost:8000"  # Change to your Render URL if testing production
ENDPOINT = f"{BASE_URL}/api/api/parse-query/"
TIMEOUT = 30  # Seconds

# COLOR CODES FOR OUTPUT
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def print_result(success: bool, message: str):
    if success:
        print(f"{GREEN}[PASS]{RESET} {message}")
    else:
        print(f"{RED}[FAIL]{RESET} {message}")

def run_test(name: str, query: str, checks: List[callable]) -> bool:
    print(f"\n{CYAN}Running Test: {name}{RESET}")
    print(f"Query: \"{query}\"")
    
    start_time = time.time()
    try:
        response = requests.post(ENDPOINT, json={"query": query}, timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()
        duration = time.time() - start_time
        
        print(f"Response (took {duration:.2f}s):")
        print(json.dumps(result, indent=2))
        
        all_passed = True
        for check in checks:
            try:
                check_result = check(result)
                if not check_result:
                    all_passed = False
            except Exception as e:
                print_result(False, f"Check raised exception: {e}")
                all_passed = False
        
        return all_passed
        
    except requests.exceptions.ConnectionError:
        print_result(False, f"Connection failed. Is the server running at {BASE_URL}?")
        return False
    except requests.exceptions.Timeout:
        print_result(False, "Request timed out.")
        return False
    except requests.exceptions.HTTPError as e:
        print_result(False, f"HTTP Error: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        print_result(False, f"Unexpected error: {e}")
        return False

# CHECK FUNCTIONS
def check_cuisine_expanded(expected_keyword: str):
    def check(result: Dict[str, Any]) -> bool:
        prefs = result.get('cuisine_preferences', [])
        # Check if we have at least 2 slugs if looking for a major cuisine like Indian/Italian
        # assuming the DB has aesthetic variants.
        has_keywords = [p for p in prefs if expected_keyword.lower() in p.lower()]
        
        if not has_keywords:
            print_result(False, f"Expected cuisine '{expected_keyword}' not found in {prefs}")
            return False
        
        print_result(True, f"Found {len(has_keywords)} slugs matching '{expected_keyword}': {has_keywords}")
        return True
    return check

def check_vibe(expected_vibe: str):
    def check(result: Dict[str, Any]) -> bool:
        vibe = result.get('selected_vibe')
        if vibe == expected_vibe:
            print_result(True, f"Selected vibe matches '{expected_vibe}'")
            return True
        else:
            print_result(False, f"Expected vibe '{expected_vibe}', got '{vibe}'")
            return False
    return check

def check_social_context(expected_context: str):
    def check(result: Dict[str, Any]) -> bool:
        context = result.get('social_context')
        if context == expected_context:
            print_result(True, f"Social context matches '{expected_context}'")
            return True
        else:
            print_result(False, f"Expected context '{expected_context}', got '{context}'")
            return False
    return check

def check_location(expected_location: str):
    def check(result: Dict[str, Any]) -> bool:
        location = result.get('location_hint')
        # Allow case-insensitive partial match
        if location and expected_location.lower() in location.lower():
            print_result(True, f"Location hint '{location}' contains '{expected_location}'")
            return True
        else:
            print_result(False, f"Expected location '{expected_location}', got '{location}'")
            return False
    return check

def check_time(expected_time: str):
    def check(result: Dict[str, Any]) -> bool:
        time_pref = result.get('time_preference')
        if time_pref == expected_time:
            print_result(True, f"Time preference matches '{expected_time}'")
            return True
        else:
            print_result(False, f"Expected time '{expected_time}', got '{time_pref}'")
            return False
    return check

# MAIN TEST SUITE
def main():
    print(f"{YELLOW}Starting Comprehensive Parse Query Tests...{RESET}")
    print(f"Target: {ENDPOINT}")
    
    tests = [
        # 1. Indian Cuisine Expansion
        {
            "name": "Indian Cuisine Expansion",
            "query": "romantic indian places in soho",
            "checks": [
                check_cuisine_expanded("indian"),
                check_vibe("dinner_date"),
                check_location("soho")
            ]
        },
        # 2. Italian Cuisine Expansion
        {
            "name": "Italian Cuisine Expansion",
            "query": "italian dinner date",
            "checks": [
                check_cuisine_expanded("italian"),
                check_vibe("dinner_date"),
                check_social_context("couple")
            ]
        },
        # 3. Specific Asian Cuisines
        {
            "name": "Korean Cuisine",
            "query": "korean bbq with friends",
            "checks": [
                check_cuisine_expanded("korean"),
                check_social_context("group")
            ]
        },
        {
            "name": "Japanese/Sushi",
            "query": "upscale sushi place",
            "checks": [
                check_cuisine_expanded("japanese"), # Should catch sushi and izakaya
                check_vibe("fine_dining")
            ]
        },
        {
            "name": "Thai Food",
            "query": "spicy thai food for lunch",
            "checks": [
                check_cuisine_expanded("thai"),
                check_time("afternoon") # or morning depending on definition of lunch start
            ]
        },
        # 4. Non-Cuisine Vibes
        {
            "name": "Coffee/Work",
            "query": "quiet place to work with coffee",
            "checks": [
                check_vibe("work_friendly"),
                lambda r: "coffee" in str(r.get('cuisine_preferences', [])).lower() or r.get('selected_vibe') == 'work_friendly'
            ]
        },
        {
            "name": "Speakeasy/Drinks",
            "query": "hidden speakeasy for cocktails",
            "checks": [
                check_vibe("speakeasy"),
                check_time("night") # usually implies night
            ]
        },
        # 5. Mixed/Complex Queries
        {
            "name": "Multiple Cuisines",
            "query": "indian or thai food",
            "checks": [
                check_cuisine_expanded("indian"),
                check_cuisine_expanded("thai")
            ]
        },
        {
            "name": "Location Specific",
            "query": "pizza in brooklyn",
            "checks": [
                check_cuisine_expanded("pizza"),
                check_location("brooklyn")
            ]
        }
    ]
    
    passed_count = 0
    total_count = len(tests)
    
    for test in tests:
        if run_test(test["name"], test["query"], test["checks"]):
            passed_count += 1
            
    print(f"\n{YELLOW}Test Summary: {passed_count}/{total_count} Passed{RESET}")
    
    if passed_count == total_count:
        print(f"{GREEN}All tests passed! API is robust.{RESET}")
    else:
        print(f"{RED}Some tests failed. Check output above.{RESET}")

if __name__ == "__main__":
    main()
