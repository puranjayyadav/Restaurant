"""
Quick test: Scrape SoHo work-friendly cafes and save to Supabase
"""

from advanced_grid_scraper import run_grid_search
from supabase_storage import save_batch_to_supabase

# Test with one neighborhood and one vibe
location = "SoHo, New York, NY"
vibe_name = "work_friendly"
search_query = "laptop friendly coffee shop with wifi and outlets"

print("="*60)
print("  TEST: Scraping SoHo for work-friendly cafes")
print("="*60 + "\n")

# 1. Scrape
print(f"🔍 Scraping '{vibe_name}' in SoHo...")
results = run_grid_search(location, search_query, grid_dimension=2)

# 2. Save to Supabase
if results:
    print(f"\n💾 Saving {len(results)} places to Supabase...")
    success = save_batch_to_supabase(results, vibe_name, "SoHo")
    
    if success:
        print("\n✅ SUCCESS! Data saved to Supabase")
        print("\nCheck your Supabase dashboard:")
        print("  - Table Editor → venues")
        print("  - Table Editor → venue_vibes")
        print("\nExample query:")
        print("  SELECT * FROM venue_vibes WHERE vibe_slug = 'work_friendly';")
    else:
        print("\n❌ Failed to save to Supabase")
else:
    print("\n⚠️  No results found")

print("\n" + "="*60)
