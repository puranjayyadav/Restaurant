"""
Small test version of cuisine_fetcher.py
Tests with just 1 neighborhood and 2 cuisines
"""

import sys
import os

# Add parent directory to path to import the main script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cuisine_fetcher import run_grid_search, SUPABASE_ENABLED

if SUPABASE_ENABLED:
    from supabase_storage import save_batch_to_supabase

import time
import random

# Test configuration
TEST_NEIGHBORHOOD = "SoHo, New York, NY"
TEST_CUISINES = {
    "pizza_nyc": "classic new york slice thin crust coal oven brick oven",
    "italian_regional": "tuscan sicilian roman pasta authentic regional specialties"
}
GRID_SIZE = 2  # Small 2x2 grid

print("=== CUISINE FETCHER TEST RUN ===")
print(f"Neighborhood: {TEST_NEIGHBORHOOD}")
print(f"Cuisines: {list(TEST_CUISINES.keys())}")
print(f"Grid Size: {GRID_SIZE}x{GRID_SIZE}")
print()

for cuisine_name, search_query in TEST_CUISINES.items():
    print(f">>> Searching for '{cuisine_name}'...")
    
    try:
        results = run_grid_search(TEST_NEIGHBORHOOD, search_query, GRID_SIZE)
        
        print(f"Found {len(results)} unique places")
        
        # Show first 3 results
        if results:
            print("\nSample results:")
            for i, place in enumerate(results[:3], 1):
                print(f"  {i}. {place.get('name')} - {place.get('full_address')}")
        
        # Save to Supabase if enabled
        if SUPABASE_ENABLED and results:
            neighborhood_name = TEST_NEIGHBORHOOD.split(',')[0].strip()
            save_batch_to_supabase(results, cuisine_name, neighborhood_name)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Short delay between cuisines
    if cuisine_name != list(TEST_CUISINES.keys())[-1]:
        print("\nWaiting 3 seconds before next cuisine...")
        time.sleep(3)
    print()

print("=== TEST COMPLETE ===")
