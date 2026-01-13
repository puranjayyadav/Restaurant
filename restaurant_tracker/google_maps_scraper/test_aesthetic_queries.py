"""
Test script for aesthetic queries in cuisine_fetcher.py
Tests with 1 neighborhood, 1 cuisine, and its aesthetic variants
"""

import sys
import os

# Add parent directory to path to import the main script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cuisine_fetcher import run_grid_search, generate_aesthetic_queries, SUPABASE_ENABLED

if SUPABASE_ENABLED:
    from supabase_storage import save_batch_to_supabase

import time
import random

# Test configuration
TEST_NEIGHBORHOOD = "SoHo"
TEST_LOCATION = f"{TEST_NEIGHBORHOOD}, New York, NY"
TEST_CUISINE_NAME = "italian_regional"
TEST_CUISINE_QUERY = "tuscan sicilian roman pasta authentic regional specialties"
GRID_SIZE = 2  # Small 2x2 grid

print("=== AESTHETIC QUERIES TEST RUN ===")
print(f"Neighborhood: {TEST_LOCATION}")
print(f"Cuisine: {TEST_CUISINE_NAME}")
print(f"Grid Size: {GRID_SIZE}x{GRID_SIZE}")
print()

# 1. Run the base cuisine search
print(f">>> STEP 1: Base cuisine search for '{TEST_CUISINE_NAME}'...")
try:
    results = run_grid_search(TEST_LOCATION, TEST_CUISINE_QUERY, GRID_SIZE)
    
    print(f"Found {len(results)} unique places")
    
    # Show first 3 results
    if results:
        print("\nSample results:")
        for i, place in enumerate(results[:3], 1):
            print(f"  {i}. {place.get('name')} - {place.get('full_address')}")
    
    # Save to Supabase if enabled
    if SUPABASE_ENABLED and results:
        save_batch_to_supabase(results, TEST_CUISINE_NAME, TEST_NEIGHBORHOOD)
        print(f"✅ Saved to Supabase with slug: '{TEST_CUISINE_NAME}'")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\nWaiting 3 seconds before aesthetic searches...")
time.sleep(3)
print()

# 2. Run aesthetic searches
print(f">>> STEP 2: Aesthetic searches for '{TEST_CUISINE_NAME}'...")
aesthetic_queries = generate_aesthetic_queries(TEST_NEIGHBORHOOD, TEST_CUISINE_QUERY)

print(f"Generated {len(aesthetic_queries)} aesthetic queries:")
for i, query in enumerate(aesthetic_queries, 1):
    print(f"  {i}. {query}")
print()

aesthetic_results_total = 0
for i, aesthetic_query in enumerate(aesthetic_queries, 1):
    print(f">>> Aesthetic Query {i}/{len(aesthetic_queries)}: '{aesthetic_query}'")
    
    try:
        results = run_grid_search(TEST_LOCATION, aesthetic_query, GRID_SIZE)
        
        print(f"Found {len(results)} unique places")
        aesthetic_results_total += len(results)
        
        # Show first 2 results
        if results:
            print("Sample results:")
            for j, place in enumerate(results[:2], 1):
                print(f"  {j}. {place.get('name')} - {place.get('full_address')}")
        
        # Save to Supabase with aesthetic slug
        if SUPABASE_ENABLED and results:
            aesthetic_slug = f"{TEST_CUISINE_NAME}_aesthetic"
            save_batch_to_supabase(results, aesthetic_slug, TEST_NEIGHBORHOOD)
            print(f"✅ Saved to Supabase with slug: '{aesthetic_slug}'")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Short delay between aesthetic queries
    if i < len(aesthetic_queries):
        print("\nWaiting 3 seconds before next aesthetic query...")
        time.sleep(3)
    print()

print("=" * 60)
print("=== TEST COMPLETE ===")
print(f"Total aesthetic results found: {aesthetic_results_total}")
print()
print("Summary:")
print(f"  - Base cuisine slug: '{TEST_CUISINE_NAME}'")
print(f"  - Aesthetic slug: '{TEST_CUISINE_NAME}_aesthetic'")
print(f"  - You can now filter by these slugs in venue_vibes!")
print("=" * 60)
