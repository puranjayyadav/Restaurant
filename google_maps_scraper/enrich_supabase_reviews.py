"""
Save scraped reviews to Supabase
Integrates with enrich_with_reviews.py and review scraper
"""

import os
from supabase import create_client
from decouple import config
from typing import List, Dict, Any

# Supabase Configuration (reuse from supabase_storage)
SUPABASE_URL = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
SUPABASE_KEY = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None


def save_reviews_to_supabase(place_id: str, reviews: List[Dict[str, Any]]) -> bool:
    """
    Saves reviews to Supabase for a specific venue.
    
    Args:
        place_id: Google Maps place_id
        reviews: List of review dictionaries with keys: author, rating, text, length
    
    Returns:
        True if successful, False otherwise
    """
    if not supabase:
        print("      [⚠️] Supabase not configured")
        return False
    
    if not reviews:
        print(f"      [ℹ️] No reviews to save for {place_id}")
        return True
    
    # Prepare review data
    reviews_data = []
    for review in reviews:
        reviews_data.append({
            "place_id": place_id,
            "author": review.get('author', 'Unknown'),
            "rating": review.get('rating'),
            "text": review.get('text', ''),
            "text_length": review.get('length', len(review.get('text', '')))
        })
    
    try:
        # Upsert reviews (will skip duplicates due to UNIQUE constraint)
        supabase.table("reviews").upsert(
            reviews_data,
            on_conflict="place_id,author,text"
        ).execute()
        
        print(f"      [✅] Saved {len(reviews)} reviews for {place_id}")
        return True
        
    except Exception as e:
        print(f"      [❌] Error saving reviews: {e}")
        return False


def get_venues_without_reviews(limit: int = 100, min_rating: float = 4.0) -> List[Dict[str, Any]]:
    """
    Get venues from Supabase that don't have reviews yet.
    
    Args:
        limit: Maximum number of venues to return
        min_rating: Minimum rating filter
    
    Returns:
        List of venue dictionaries
    """
    if not supabase:
        return []
    
    try:
        # Get venues with high ratings that don't have reviews
        # Check for both null and 0 review count
        response = (
            supabase.table("venues")
            .select("place_id, name, rating")
            .gte("rating", min_rating)
            .or_("scraped_review_count.is.null,scraped_review_count.eq.0")
            .limit(limit)
            .execute()
        )
        
        return response.data
        
    except Exception as e:
        print(f"Error fetching venues: {e}")
        return []


def batch_enrich_venues_with_reviews(max_venues: int = 10, max_reviews_per_venue: int = 5):
    """
    Fetch venues from Supabase and enrich them with reviews.
    
    This is the main function to run the review enrichment process.
    """
    if not supabase:
        print("❌ Supabase not configured")
        return
    
    # Import here to avoid circular dependency
    import subprocess
    import json
    import os
    
    print(f"\n{'='*60}")
    print(f"  BATCH REVIEW ENRICHMENT")
    print(f"{'='*60}\n")
    
    # Get venues without reviews
    print(f"📂 Fetching venues without reviews...")
    venues = get_venues_without_reviews(limit=max_venues, min_rating=4.0)
    
    if not venues:
        print("✅ All venues already have reviews!")
        return
    
    print(f"   Found {len(venues)} venues to enrich\n")
    
    # Path to Node scraper
    scraper_dir = os.path.join(os.path.dirname(__file__), 'review_scraper_test')
    scraper_script = os.path.join(scraper_dir, 'final_scraper.js')
    reviews_output = os.path.join(scraper_dir, 'final_reviews.json')
    
    enriched_count = 0
    failed_count = 0
    
    for i, venue in enumerate(venues):
        place_id = venue['place_id']
        name = venue['name']
        
        print(f"[{i+1}/{len(venues)}] 🔍 {name}")
        print(f"   Place ID: {place_id}")
        
        try:
            # Run Node scraper with place_id
            result = subprocess.run(
                ['node', 'final_scraper.js', place_id, str(max_reviews_per_venue)],
                cwd=scraper_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check if reviews file was created
            if os.path.exists(reviews_output):
                with open(reviews_output, 'r', encoding='utf-8') as f:
                    reviews = json.load(f)
                
                if reviews and len(reviews) > 0:
                    # Save to Supabase
                    success = save_reviews_to_supabase(place_id, reviews)
                    if success:
                        enriched_count += 1
                else:
                    print(f"   ⚠️  No reviews found")
                
                # Clean up
                os.remove(reviews_output)
            else:
                failed_count += 1
                print(f"   ❌ Failed to fetch reviews")
            
            # Rate limiting
            if i < len(venues) - 1:
                import time
                delay = 12
                print(f"   ⏳ Waiting {delay}s...")
                time.sleep(delay)
        
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  Timeout - skipping")
            failed_count += 1
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed_count += 1
    
    print(f"\n{'='*60}")
    print(f"  ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successfully enriched: {enriched_count} venues")
    print(f"❌ Failed: {failed_count} venues")
    print(f"\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        max_venues = int(sys.argv[1])
    else:
        max_venues = 5  # Default: enrich 5 venues
    
    print("\n🔍 Review Enrichment for Supabase Venues\n")
    
    if not supabase:
        print("❌ Supabase not configured!")
        print("\nSet these environment variables:")
        print("  SUPABASE_URL=your_url")
        print("  SUPABASE_KEY=your_key\n")
        sys.exit(1)
    
    print(f"✅ Supabase connected")
    print(f"📊 Will enrich up to {max_venues} venues\n")
    
    batch_enrich_venues_with_reviews(max_venues=max_venues, max_reviews_per_venue=5)
