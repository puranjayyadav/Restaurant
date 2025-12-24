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

from advanced_grid_scraper import run_grid_search
from supabase_storage import save_batch_to_supabase, supabase
from enrich_supabase_reviews import batch_enrich_venues_with_reviews

# Configuration
VIBES_PER_RUN = 5  # Scrape 5 vibes per run (15 min schedule = ~20 vibes/hour)
REVIEWS_PER_RUN = 15  # Enrich 15 venues with reviews per run

# Define a subset of vibes to rotate through
VIBE_ROTATION = [
    ("work_friendly", "laptop friendly coffee shop with wifi and outlets"),
    ("aesthetic", "instagrammable cute cafe pastel decor"),
    ("speakeasy", "hidden speakeasy bar entrance behind bookshelf"),
    ("coffee_run", "specialty coffee roasters espresso bar grab and go"),
    ("brunch_buzzy", "popular brunch spot avocado toast bottomless mimosas"),
    ("rooftop", "rooftop bar with skyline view"),
    ("natural_wine", "natural wine bar organic funky orange wine"),
    ("dinner_date", "romantic dinner restaurant candlelit cozy atmosphere"),
]

# Neighborhoods to cycle through
NEIGHBORHOODS = [
    "SoHo, New York, NY",
    "Williamsburg, New York, NY",
    "East Village, New York, NY",
    "West Village, New York, NY",
    "Tribeca, New York, NY",
]

def get_next_vibe_and_neighborhood():
    """
    Rotate through vibes and neighborhoods to avoid scraping the same thing repeatedly.
    Uses a simple file-based counter.
    """
    counter_file = "scraper_counter.txt"
    
    if os.path.exists(counter_file):
        with open(counter_file, 'r') as f:
            counter = int(f.read().strip())
    else:
        counter = 0
    
    # Get vibe and neighborhood based on counter
    vibe_idx = counter % len(VIBE_ROTATION)
    neighborhood_idx = (counter // len(VIBE_ROTATION)) % len(NEIGHBORHOODS)
    
    vibe_name, search_query = VIBE_ROTATION[vibe_idx]
    neighborhood = NEIGHBORHOODS[neighborhood_idx]
    
    # Increment counter
    with open(counter_file, 'w') as f:
        f.write(str(counter + 1))
    
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
