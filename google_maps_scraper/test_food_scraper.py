"""
Trial run script for food_type_scraper.py
Tests a few food types in one neighborhood to verify functionality.
"""

import sys
import os

# Add the current directory to path so we can import from food_type_scraper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from food_type_scraper import run_grid_search, FOOD_TYPE_LIST, SUPABASE_ENABLED
from supabase_storage import save_batch_to_supabase
import time
import random

# --- TRIAL SETTINGS ---
GRID_SIZE = 2
TEST_NEIGHBORHOOD = "SoHo"  # Single neighborhood for testing
TEST_FOOD_TYPES = [
    "ice_cream_parlor",
    "pizza_place", 
    "sushi_restaurant"
]  # Just 3 food types for trial

print("=" * 60)
print("TRIAL RUN: Food Type Scraper")
print("=" * 60)
print(f"Neighborhood: {TEST_NEIGHBORHOOD}")
print(f"Food Types: {', '.join(TEST_FOOD_TYPES)}")
print(f"Grid Size: {GRID_SIZE}")
print("=" * 60)
print()

location_string = f"{TEST_NEIGHBORHOOD}, New York, NY"

for food_type_name in TEST_FOOD_TYPES:
    if food_type_name not in FOOD_TYPE_LIST:
        print(f"   [!] Warning: '{food_type_name}' not found in FOOD_TYPE_LIST, skipping...")
        continue
    
    search_query = FOOD_TYPE_LIST[food_type_name]
    print(f"\n>> Testing '{food_type_name}' ({search_query})...")
    
    try:
        results = run_grid_search(location_string, search_query, GRID_SIZE)
        print(f"   [OK] Found {len(results)} unique places")
        
        # Save to Supabase if enabled
        if SUPABASE_ENABLED and results:
            print(f"   [INFO] Saving to Supabase...")
            success = save_batch_to_supabase(results, food_type_name, TEST_NEIGHBORHOOD)
            if success:
                print(f"   [SUCCESS] Saved {len(results)} venues to Supabase")
            else:
                print(f"   [WARNING] Failed to save to Supabase")
        elif not SUPABASE_ENABLED:
            print(f"   [INFO] Supabase not enabled, skipping save")
        elif not results:
            print(f"   [INFO] No results to save")
        
        # Show first 3 results as sample
        if results:
            print("\n   Sample results:")
            for i, place in enumerate(results[:3], 1):
                print(f"   {i}. {place.get('name', 'N/A')} - {place.get('full_address', 'N/A')}")
                print(f"      Rating: {place.get('avg_rating', 'N/A')}, Reviews: {place.get('total_reviews', 'N/A')}")
        else:
            print("   No results found for this food type.")
            
    except Exception as e:
        print(f"   [!] Error: {e}")
        import traceback
        traceback.print_exc()
        continue
    
    # Short delay between food types
    sleep_seconds = random.uniform(3, 6)
    print(f"\n   [Waiting {sleep_seconds:.1f}s before next food type...]")
    time.sleep(sleep_seconds)

print("\n" + "=" * 60)
print("TRIAL RUN COMPLETE")
print("=" * 60)
