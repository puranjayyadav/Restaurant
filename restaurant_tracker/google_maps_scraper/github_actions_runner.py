"""
GitHub Actions Orchestrator
Runs venue scraping and review enrichment on a schedule
"""

import os
import sys
import time
import random
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from advanced_grid_scraper import run_grid_search, VIBE_LIST, NYC_AREAS
from supabase_storage import save_batch_to_supabase, supabase
from enrich_supabase_reviews import batch_enrich_venues_with_reviews

# Configuration
VIBES_PER_RUN = 5  # Scrape 5 vibes per run (15 min schedule = ~20 vibes/hour)
REVIEWS_PER_RUN = 15  # Enrich 15 venues with reviews per run

# Flatten VIBE_LIST to list of tuples for rotation
VIBE_ROTATION = list(VIBE_LIST.items())

# Flatten NYC_AREAS to a simple list of "Neighborhood, New York, NY"
NEIGHBORHOODS = []
for area_group in NYC_AREAS.values():
    for neighborhood in area_group:
        NEIGHBORHOODS.append(f"{neighborhood}, New York, NY")

def get_next_vibe_and_neighborhood():
    """
    Rotate through vibes and neighborhoods to avoid scraping the same thing repeatedly.
    Uses Supabase to persist state (avoiding git commit conflicts).
    """
    if not supabase:
        # Fallback to random if Supabase fails
        import random
        vibe_idx = random.randint(0, len(VIBE_ROTATION) - 1)
        neighborhood_idx = random.randint(0, len(NEIGHBORHOODS) - 1)
        vibe_name, search_query = VIBE_ROTATION[vibe_idx]
        neighborhood = NEIGHBORHOODS[neighborhood_idx]
        return vibe_name, search_query, neighborhood

    try:
        # 1. Fetch current index from 'scraper_state' table
        # We assume a single row with id=1 stores the state
        response = supabase.table("scraper_state").select("last_index").eq("id", 1).execute()
        
        if response.data:
            counter = response.data[0]['last_index']
        else:
            # Initialize table if empty
            counter = 0
            supabase.table("scraper_state").insert({"id": 1, "last_index": 0}).execute()
        
        # 2. Calculate next targets
        total_combinations = len(VIBE_ROTATION) * len(NEIGHBORHOODS)
        
        # Determine strict indices
        vibe_idx = counter % len(VIBE_ROTATION)
        neighborhood_idx = (counter // len(VIBE_ROTATION)) % len(NEIGHBORHOODS)
        
        vibe_name, search_query = VIBE_ROTATION[vibe_idx]
        neighborhood = NEIGHBORHOODS[neighborhood_idx]
        
        # 3. Increment and Save back to Supabase
        new_counter = (counter + 1) % total_combinations # Wrap around eventually
        supabase.table("scraper_state").update({"last_index": new_counter}).eq("id", 1).execute()
        
        return vibe_name, search_query, neighborhood
        
    except Exception as e:
        print(f"Error managing state with Supabase: {e}")
        # Fallback to random
        import random
        vibe_idx = random.randint(0, len(VIBE_ROTATION) - 1)
        neighborhood_idx = random.randint(0, len(NEIGHBORHOODS) - 1)
        vibe_name, search_query = VIBE_ROTATION[vibe_idx]
        neighborhood = NEIGHBORHOODS[neighborhood_idx]
        return vibe_name, search_query, neighborhood


def run_venue_scraping():
    """Scrape venues and save to Supabase"""
    print("\n" + "="*60)
    print("  VENUE SCRAPING")
    print("="*60 + "\n")
    
    if not supabase:
        print("❌ Supabase not configured")
        return False
    
    overall_success = True
    
    for i in range(VIBES_PER_RUN):
        print(f"\n--- Batch {i+1}/{VIBES_PER_RUN} ---")
        
        try:
            # Get next vibe and neighborhood
            vibe_name, search_query, neighborhood = get_next_vibe_and_neighborhood()
            
            print(f"📍 Location: {neighborhood}")
            print(f"🎯 Vibe: {vibe_name}")
            print(f"🔍 Query: {search_query}\n")
            
            # Run scraper
            results = run_grid_search(neighborhood, search_query, grid_dimension=2)
            
            # Save to Supabase
            if results:
                neighborhood_name = neighborhood.split(',')[0]  # Extract just "SoHo"
                success = save_batch_to_supabase(results, vibe_name, neighborhood_name)
                
                if success:
                    print(f"\n✅ Scraped and saved {len(results)} venues")
                else:
                    print("\n❌ Failed to save to Supabase")
                    overall_success = False
            else:
                print("\n⚠️  No results found")
                # Don't mark as failure, just empty
            
            # Sleep between batches to respect rate limits/avoid blocking
            if i < VIBES_PER_RUN - 1:
                sleep_time = random.uniform(5, 10)
                print(f"Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                
        except Exception as e:
            print(f"\n❌ Error during venue scraping batch {i+1}: {e}")
            import traceback
            traceback.print_exc()
            overall_success = False
            
    return overall_success


def run_review_enrichment():
    """Enrich venues with reviews"""
    print("\n" + "="*60)
    print("  REVIEW ENRICHMENT")
    print("="*60 + "\n")
    
    if not supabase:
        print("❌ Supabase not configured")
        return False
    
    try:
        batch_enrich_venues_with_reviews(
            max_venues=REVIEWS_PER_RUN,
            max_reviews_per_venue=5
        )
        return True
        
    except Exception as e:
        print(f"\n❌ Error during review enrichment: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main orchestrator function"""
    start_time = datetime.now()
    
    print("\n" + "="*60)
    print(f"  GITHUB ACTIONS SCRAPER RUN")
    print(f"  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Check Supabase connection
    if not supabase:
        print("\n❌ CRITICAL: Supabase not configured!")
        print("Set SUPABASE_URL and SUPABASE_KEY in GitHub Secrets")
        sys.exit(1)
    
    print("\n✅ Supabase connected")
    
    # Step 1: Scrape venues
    venue_success = run_venue_scraping()
    
    # Small delay between operations
    time.sleep(5)
    
    # Step 2: Enrich with reviews
    review_success = run_review_enrichment()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("  RUN COMPLETE")
    print("="*60)
    print(f"Duration: {duration:.1f} seconds")
    print(f"Venue Scraping: {'✅ Success' if venue_success else '❌ Failed'}")
    print(f"Review Enrichment: {'✅ Success' if review_success else '❌ Failed'}")
    print("="*60 + "\n")
    
    # Exit with error code if either failed
    if not (venue_success or review_success):
        sys.exit(1)


if __name__ == "__main__":
    main()
