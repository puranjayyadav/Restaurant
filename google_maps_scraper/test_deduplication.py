"""
Test deduplication - runs the same search twice to verify no duplicates are created
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cuisine_fetcher import run_grid_search, SUPABASE_ENABLED

if SUPABASE_ENABLED:
    from supabase_storage import save_batch_to_supabase

print("=== DEDUPLICATION TEST ===")
print("This test will run the same search TWICE to verify duplicates are prevented\n")

TEST_LOCATION = "SoHo, New York, NY"
TEST_QUERY = "pizza"
GRID_SIZE = 2

print(f">>> FIRST RUN: Searching for '{TEST_QUERY}' in {TEST_LOCATION}")
results1 = run_grid_search(TEST_LOCATION, TEST_QUERY, GRID_SIZE)
print(f"Found {len(results1)} unique places\n")

if SUPABASE_ENABLED and results1:
    print("Saving to Supabase with vibe 'test_pizza'...")
    save_batch_to_supabase(results1, "test_pizza", "SoHo")
    print()

print("=" * 60)
print(">>> SECOND RUN: Running THE EXACT SAME SEARCH again...")
print("=" * 60)
print()

results2 = run_grid_search(TEST_LOCATION, TEST_QUERY, GRID_SIZE)
print(f"Found {len(results2)} unique places\n")

if SUPABASE_ENABLED and results2:
    print("Saving to Supabase AGAIN with the same vibe 'test_pizza'...")
    save_batch_to_supabase(results2, "test_pizza", "SoHo")
    print()

print("=" * 60)
print("=== TEST COMPLETE ===")
print()
print("Expected behavior:")
print("  ✅ First run: Inserts new venues into database")
print("  ✅ Second run: Updates existing venues (no duplicates created)")
print("  ✅ Venue_vibes: No duplicate place_id+vibe_slug combinations")
print()
print("Check your Supabase 'venues' table - you should see:")
print(f"  - {len(results1)} venues (not {len(results1) + len(results2)}!)")
print("  - Each venue appears only ONCE")
print("  - 'updated_at' timestamp should be newer for second run")
print("=" * 60)
