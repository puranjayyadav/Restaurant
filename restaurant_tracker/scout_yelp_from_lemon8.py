"""
Scout: Discovers Yelp URLs from Lemon8 articles and saves them to Supabase crawl_queue_yelp table.

Workflow:
1. Query Supabase lemon8_articles table for itinerary_data (only unprocessed articles)
2. Extract place_name from stops
3. Check if Yelp URL already exists in crawl_queue_yelp
4. Find Yelp URLs using yelp_url_enricher
5. Save Yelp URLs to crawl_queue_yelp table in Supabase
"""

import os
import sys
import time
import argparse
from typing import List, Dict, Optional
from urllib.parse import urlparse

# Force unbuffered output for CI environments
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

print("=" * 60, flush=True)
print("SCOUT STARTED - scout_yelp_from_lemon8.py", flush=True)
print("=" * 60, flush=True)
sys.stdout.flush()

from supabase_config import (
    get_supabase_client, 
    add_yelp_url_to_queue, 
    get_processed_article_urls_for_yelp
)
from yelp_url_enricher import find_yelp_url


def extract_yelp_id_from_url(url: str) -> Optional[str]:
    """Extract Yelp business ID from URL"""
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'biz':
            return path_parts[1]
    except:
        pass
    return None


def get_existing_yelp_ids() -> set:
    """Get all existing Yelp IDs from crawl_queue_yelp table"""
    supabase = get_supabase_client()
    if not supabase:
        return set()
    
    try:
        result = supabase.table("crawl_queue_yelp")\
            .select("yelp_id")\
            .execute()
        
        yelp_ids = set()
        if result.data:
            for row in result.data:
                yelp_id = row.get("yelp_id")
                if yelp_id:
                    yelp_ids.add(yelp_id)
        
        return yelp_ids
    except Exception as e:
        print(f"⚠️  Error loading existing Yelp IDs: {e}")
        return set()


def get_restaurants_from_lemon8_articles(limit: Optional[int] = None, processed_article_urls: set = None) -> List[Dict]:
    """
    Query Supabase lemon8_articles table and extract restaurant names from itinerary_data.
    Only queries articles that haven't been processed for Yelp URL discovery yet.
    
    Args:
        limit: Limit number of articles to process
        processed_article_urls: Set of article URLs that have already been processed
    
    Returns:
        List of dictionaries with restaurant info: {
            'place_name': str,
            'city': str,
            'category': str,
            'notes': str,
            'article_url': str
        }
    """
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Could not connect to Supabase", flush=True)
        return []
    
    if processed_article_urls is None:
        processed_article_urls = set()
    
    try:
        # Query articles that have itinerary_data
        query = supabase.table("lemon8_articles")\
            .select("url, itinerary_data")\
            .not_.is_("itinerary_data", "null")
        
        # Order by created_at to process oldest first
        query = query.order("created_at", desc=False)
        
        if limit:
            query = query.limit(limit * 10)  # Get more articles to account for filtering
        
        response = query.execute()
        
        restaurants = []
        seen_places = set()  # Avoid duplicates
        processed_count = 0
        
        for article in response.data:
            article_url = article.get("url")
            
            # Skip if this article has already been processed
            if article_url in processed_article_urls:
                processed_count += 1
                continue
            
            itinerary_data = article.get("itinerary_data")
            
            if not itinerary_data:
                continue
            
            # Extract city from itinerary_data
            city = itinerary_data.get("city", "New York")  # Default to NYC
            
            # Extract stops (restaurants/places)
            stops = itinerary_data.get("stops", [])
            
            for stop in stops:
                place_name = stop.get("place_name")
                category = stop.get("category", "Food")
                notes = stop.get("notes", "")
                
                if not place_name:
                    continue
                
                # Create unique key to avoid duplicates
                place_key = f"{place_name.lower()}_{city.lower()}"
                
                if place_key not in seen_places:
                    seen_places.add(place_key)
                    restaurants.append({
                        'place_name': place_name,
                        'city': city,
                        'category': category,
                        'notes': notes,
                        'article_url': article_url
                    })
            
            # Apply limit based on number of restaurants found, not articles
            if limit and len(restaurants) >= limit:
                break
        
        print(f"  Skipped {processed_count} already-processed articles", flush=True)
        return restaurants
        
    except Exception as e:
        print(f"ERROR: Failed to query Supabase: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return []


def scout_yelp_urls(
    limit: Optional[int] = 100,
    headless: bool = True,
    delay: float = 2.0
):
    """
    Scout function: Discover Yelp URLs from Lemon8 articles and save to Supabase crawl_queue_yelp table.
    Processes in batches and automatically continues from where it left off.
    
    Args:
        limit: Number of restaurants to process per batch (default: 100)
        headless: Run browser in headless mode
        delay: Delay between searches
    """
    print("="*60, flush=True)
    print("🔍 YELP URL SCOUT - Discovering Yelp URLs from Lemon8", flush=True)
    print(f"📦 Batch size: {limit} restaurants", flush=True)
    print("="*60, flush=True)
    print(flush=True)
    
    # Load existing data from Supabase
    print("📂 Loading existing data from Supabase...", flush=True)
    existing_yelp_ids = get_existing_yelp_ids()
    processed_article_urls = get_processed_article_urls_for_yelp()
    
    print(f"✅ Found {len(existing_yelp_ids)} existing Yelp IDs in crawl_queue_yelp", flush=True)
    print(f"✅ Found {len(processed_article_urls)} already-processed articles", flush=True)
    print(flush=True)
    
    # Step 1: Get restaurants from Lemon8 articles (only unprocessed ones)
    print(f"📋 Step 1: Querying Supabase for up to {limit} restaurants from unprocessed Lemon8 articles...", flush=True)
    restaurants_to_enrich = get_restaurants_from_lemon8_articles(
        limit=limit, 
        processed_article_urls=processed_article_urls
    )
    print(f"✅ Found {len(restaurants_to_enrich)} unique restaurants to process in this batch", flush=True)
    print(flush=True)
    
    if not restaurants_to_enrich:
        print("❌ No restaurants found to enrich. All articles have been processed.", flush=True)
        return
    
    # Step 2: Find Yelp URLs (only for new restaurants)
    print(f"🔍 Step 2: Finding Yelp URLs for batch of {len(restaurants_to_enrich)} restaurants...", flush=True)
    found_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for i, restaurant in enumerate(restaurants_to_enrich, 1):
        place_name = restaurant['place_name']
        city = restaurant['city']
        
        # Need to find Yelp URL
        print(f"  [{i}/{len(restaurants_to_enrich)}] Searching for: {place_name} ({city})", flush=True)
        
        yelp_url = find_yelp_url(place_name, city, headless=headless)
        
        if yelp_url:
            yelp_id = extract_yelp_id_from_url(yelp_url)
            
            if not yelp_id:
                print(f"    ⚠️  Could not extract Yelp ID from URL: {yelp_url}", flush=True)
                not_found_count += 1
                time.sleep(delay)
                continue
            
            # Check if this Yelp ID is already in our database
            if yelp_id in existing_yelp_ids:
                skipped_count += 1
                print(f"    ⏭️  Yelp URL already in queue: {yelp_url}", flush=True)
            else:
                # Save to Supabase
                success = add_yelp_url_to_queue(
                    yelp_id=yelp_id,
                    yelp_url=yelp_url,
                    place_name=place_name,
                    city=city,
                    lemon8_source=restaurant,
                    status="pending"
                )
                
                if success:
                    found_count += 1
                    existing_yelp_ids.add(yelp_id)  # Add to local set to avoid duplicates in same run
                    print(f"    ✅ Found and saved: {yelp_url}", flush=True)
                else:
                    print(f"    ⚠️  Failed to save to database: {yelp_url}", flush=True)
        else:
            not_found_count += 1
            print(f"    ❌ Not found", flush=True)
        
        time.sleep(delay)
    
    print(f"\n✅ Batch completed: Found {found_count} new Yelp URLs, skipped {skipped_count} already discovered, {not_found_count} not found", flush=True)
    print(flush=True)
    
    if found_count == 0 and skipped_count == 0:
        print("⏭️  No new Yelp URLs to add to queue.", flush=True)
        return
    
    # Step 3: Summary
    print()
    print("="*60, flush=True)
    print("📊 BATCH SUMMARY", flush=True)
    print("="*60, flush=True)
    print(f"✅ New URLs discovered: {found_count}", flush=True)
    print(f"⏭️  Skipped (already discovered): {skipped_count}", flush=True)
    print(f"❌ Not found: {not_found_count}", flush=True)
    print(f"📊 Total URLs in crawl_queue_yelp: {len(existing_yelp_ids) + found_count}", flush=True)
    print(f"💾 Saved to Supabase table: crawl_queue_yelp", flush=True)
    print(f"🔄 Next batch will continue from where this one left off", flush=True)
    print("="*60, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scout Yelp URLs from Lemon8 articles (processes in batches of 100)')
    parser.add_argument('--limit', type=int, default=100, help='Number of restaurants to process per batch (default: 100)')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between searches in seconds')
    
    args = parser.parse_args()
    
    scout_yelp_urls(
        limit=args.limit,
        headless=not args.visible,
        delay=args.delay
    )

