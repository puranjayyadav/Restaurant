"""
Review Enrichment Script
Adds Google Maps reviews to scraped places using the Node.js Puppeteer scraper
"""

import json
import subprocess
import time
import os
from typing import List, Dict, Any

def enrich_places_with_reviews(
    input_file: str, 
    output_file: str, 
    max_reviews_per_place: int = 5,
    max_places: int = None,
    min_rating: float = 4.0
):
    """
    Enrich scraped places with reviews from Google Maps
    
    Args:
        input_file: JSON file with scraped places
        output_file: Where to save enriched data
        max_reviews_per_place: Max reviews to fetch per place
        max_places: Limit number of places to process (None = all)
        min_rating: Only fetch reviews for places with this rating or higher
    """
    
    # Load places
    print(f"📂 Loading places from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        places = json.load(f)
    
    print(f"   Found {len(places)} places")
    
    # Filter by rating
    if min_rating:
        places = [p for p in places if (p.get('avg_rating') or 0) >= min_rating]
        print(f"   Filtered to {len(places)} places with rating >= {min_rating}")
    
    # Limit if specified
    if max_places:
        places = places[:max_places]
        print(f"   Processing first {len(places)} places")
    
    # Path to Node scraper
    scraper_dir = os.path.join(os.path.dirname(__file__), 'review_scraper_test')
    scraper_script = os.path.join(scraper_dir, 'final_scraper.js')
    reviews_output = os.path.join(scraper_dir, 'final_reviews.json')
    
    if not os.path.exists(scraper_script):
        print(f"❌ Error: {scraper_script} not found!")
        return
    
    print(f"\n🚀 Starting review enrichment...\n")
    
    enriched_count = 0
    failed_count = 0
    
    for i, place in enumerate(places):
        place_name = place.get('name', 'Unknown')
        place_id = place.get('place_id', '')
        
        # Use place_id if available, otherwise fall back to name
        search_param = place_id if place_id else place_name
        method = "place_id" if place_id else "name"
        
        print(f"[{i+1}/{len(places)}] 🔍 {place_name} (using {method})")
        
        try:
            # Run Node scraper with place_id or name
            result = subprocess.run(
                ['node', 'final_scraper.js', search_param, str(max_reviews_per_place)],
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
                    place['reviews'] = reviews
                    place['review_count'] = len(reviews)
                    enriched_count += 1
                    print(f"   ✅ Added {len(reviews)} reviews")
                else:
                    place['reviews'] = []
                    place['review_count'] = 0
                    print(f"   ⚠️  No reviews found")
                
                # Clean up
                os.remove(reviews_output)
            else:
                place['reviews'] = []
                place['review_count'] = 0
                failed_count += 1
                print(f"   ❌ Failed to fetch reviews")
            
            # Rate limiting - important!
            if i < len(places) - 1:
                delay = 12  # 12 seconds between requests
                print(f"   ⏳ Waiting {delay}s...")
                time.sleep(delay)
        
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  Timeout - skipping")
            place['reviews'] = []
            place['review_count'] = 0
            failed_count += 1
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            place['reviews'] = []
            place['review_count'] = 0
            failed_count += 1
    
    # Save enriched data
    print(f"\n💾 Saving enriched data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(places, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"  ENRICHMENT COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successfully enriched: {enriched_count} places")
    print(f"❌ Failed: {failed_count} places")
    print(f"📊 Total reviews added: {sum(p.get('review_count', 0) for p in places)}")
    print(f"💾 Saved to: {output_file}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python enrich_with_reviews.py <input_file.json> [output_file.json] [max_places]")
        print("\nExample:")
        print("  python enrich_with_reviews.py Financial_District_coffee.json enriched_output.json 10")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.json', '_with_reviews.json')
    max_places = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    enrich_places_with_reviews(
        input_file=input_file,
        output_file=output_file,
        max_reviews_per_place=5,
        max_places=max_places,
        min_rating=4.0  # Only enrich highly-rated places
    )
