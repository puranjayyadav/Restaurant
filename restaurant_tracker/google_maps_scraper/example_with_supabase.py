"""
Example: Running the scraper with Supabase integration

This script shows how to use advanced_grid_scraper.py with Supabase storage.
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from advanced_grid_scraper import run_grid_search, GRID_SIZE
from supabase_storage import save_batch_to_supabase, supabase, create_tables_if_not_exist
import time
import random

# First time setup: Print table creation SQL
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SUPABASE SETUP CHECK")
    print("="*60)
    
    if not supabase:
        print("\n❌ Supabase not configured!")
        print("\nPlease set these environment variables:")
        print("  SUPABASE_URL=your_supabase_url")
        print("  SUPABASE_KEY=your_supabase_anon_key")
        print("\nOr create a .env file with these values.\n")
        create_tables_if_not_exist()
        sys.exit(1)
    
    print("\n✅ Supabase connected!")
    print(f"   Ready to save data to database\n")
    
    # Example: Scrape one neighborhood with one vibe
    print("="*60)
    print("  EXAMPLE: Scraping SoHo for work-friendly cafes")
    print("="*60 + "\n")
    
    location = "SoHo, New York, NY"
    vibe_name = "work_friendly"
    search_query = "laptop friendly coffee shop with wifi and outlets"
    
    try:
        # 1. Run the scraper
        print(f"🔍 Scraping '{vibe_name}' in SoHo...")
        results = run_grid_search(location, search_query, grid_dimension=2)
        
        # 2. Save to Supabase
        if results:
            print(f"\n💾 Saving {len(results)} places to Supabase...")
            success = save_batch_to_supabase(results, vibe_name, "SoHo")
            
            if success:
                print("\n✅ SUCCESS! Data saved to Supabase")
                print("\nYou can now query your data:")
                print("  - All work-friendly places: SELECT * FROM venue_vibes WHERE vibe_slug = 'work_friendly'")
                print("  - All SoHo venues: SELECT * FROM venue_vibes WHERE neighborhood = 'SoHo'")
                print("  - Join for full details: SELECT v.*, vv.vibe_slug FROM venues v JOIN venue_vibes vv ON v.place_id = vv.place_id")
            else:
                print("\n❌ Failed to save to Supabase (check logs above)")
        else:
            print("\n⚠️  No results found")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("  EXAMPLE COMPLETE")
    print("="*60 + "\n")
    
    print("To run the full scraper with Supabase:")
    print("  1. Make sure tables are created (run the SQL from supabase_storage.py)")
    print("  2. Edit advanced_grid_scraper.py main loop to capture return value")
    print("  3. Call save_batch_to_supabase() after each run_grid_search()")
    print("\nSee advanced_grid_scraper.py lines 515-520 for integration example.\n")
