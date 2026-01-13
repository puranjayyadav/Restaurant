"""
Process missing Yelp restaurants from crawl_queue_yelp that are not in yelp_restaurants table.

This script:
1. Gets all restaurants from crawl_queue_yelp table
2. Gets all existing yelp_id from yelp_restaurants table
3. Finds restaurants in queue that are NOT in yelp_restaurants
4. Processes those missing restaurants using the miner logic
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
print("PROCESS MISSING YELP RESTAURANTS", flush=True)
print("=" * 60, flush=True)
sys.stdout.flush()

from scrapers.yelp_scraper import scrape_restaurant_detail, find_brave_path
from playwright.sync_api import sync_playwright
from supabase_config import (
    get_all_yelp_urls_from_queue,
    get_existing_scraped_yelp_ids,
    mark_yelp_url_processing,
    mark_yelp_url_completed,
    mark_yelp_url_failed,
    save_yelp_restaurant_to_db,
    get_yelp_queue_stats
)


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


def convert_yelp_data_to_dict(yelp_data: Dict, place_info: Dict, yelp_id: str, yelp_url: str) -> Dict:
    """
    Convert scraped Yelp data to dictionary format.
    
    Args:
        yelp_data: Dictionary from scrape_restaurant_detail
        place_info: Original place info from Lemon8 (for fallback data)
        yelp_id: Yelp business ID
        yelp_url: Yelp URL
    
    Returns:
        Dictionary with restaurant data
    """
    # Extract address components
    address = yelp_data.get("address", "")
    city = place_info.get("city", "New York")
    state = "NY"  # Default, could be extracted from address
    
    # Parse address to extract state if possible
    if address:
        address_parts = address.split(',')
        if len(address_parts) >= 2:
            state = address_parts[-1].strip().split()[0] if len(address_parts[-1].strip().split()) > 0 else "NY"
            city = address_parts[-2].strip() if len(address_parts) >= 2 else city
    
    # Extract categories/cuisine
    categories = []
    if yelp_data.get("cuisine"):
        categories = [c.strip() for c in yelp_data.get("cuisine", "").split(',')]
    if place_info.get("category") and place_info["category"] not in categories:
        categories.append(place_info["category"])
    
    # Extract hours
    hours = {}
    if yelp_data.get("hours"):
        hours_str = yelp_data.get("hours")
        if isinstance(hours_str, str):
            hours = {"raw": hours_str}
        elif isinstance(hours_str, dict):
            hours = hours_str
    
    # Extract photos
    photos = []
    if yelp_data.get("photos"):
        photos = yelp_data.get("photos", [])
    elif yelp_data.get("images"):
        photos = yelp_data.get("images", [])
    
    # Extract menu items
    menu_items = []
    if yelp_data.get("menu_items"):
        menu_items = yelp_data.get("menu_items", [])
    
    # Extract popular dishes
    popular_dishes = []
    if yelp_data.get("popular_dishes"):
        popular_dishes = yelp_data.get("popular_dishes", [])
    
    # Extract reviews
    reviews = []
    if yelp_data.get("reviews"):
        reviews = yelp_data.get("reviews", [])
    
    # Build restaurant dictionary
    restaurant = {
        "yelp_id": yelp_id,
        "source": "yelp",
        "source_id": yelp_id,
        "source_url": yelp_url,
        "url": yelp_url,
        "name": yelp_data.get("name", place_info.get("place_name", "Unknown")),
        "description": yelp_data.get("description"),
        "address": address,
        "city": city,
        "state": state,
        "rating": yelp_data.get("rating"),
        "total_reviews": yelp_data.get("total_reviews") or yelp_data.get("review_count"),
        "review_count": yelp_data.get("review_count") or yelp_data.get("total_reviews"),
        "price_range": yelp_data.get("price_range"),
        "phone": yelp_data.get("phone"),
        "website": yelp_data.get("website"),
        "hours": hours,
        "categories": categories,
        "cuisine": ", ".join(categories) if categories else None,
        "photos": photos,
        "images": photos,
        "image_urls": photos,
        "menu_items": menu_items,
        "popular_dishes": popular_dishes,
        "reviews": reviews,
        "menu_link": yelp_data.get("menu_link"),
        "amenities": yelp_data.get("amenities", []),
        "location": yelp_data.get("location"),
        "lemon8_source": place_info if place_info else None
    }
    
    return restaurant


def process_missing_restaurants(limit: Optional[int] = None, headless: bool = False, delay: float = 2.0):
    """Process restaurants from queue that are not in yelp_restaurants table"""
    
    # Check Supabase connection
    print("🔍 Checking Supabase connection...", flush=True)
    from supabase_config import get_supabase_client
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to connect to Supabase!", flush=True)
        return
    
    print("✅ Connected to Supabase", flush=True)
    
    # Get all restaurants from queue
    print("\n📂 Loading restaurants from crawl_queue_yelp...", flush=True)
    all_queue_restaurants = get_all_yelp_urls_from_queue(limit=None)  # Get all, we'll filter
    print(f"✅ Found {len(all_queue_restaurants)} restaurants in queue", flush=True)
    
    # Get existing yelp_ids from yelp_restaurants
    print("\n📂 Loading existing restaurants from yelp_restaurants...", flush=True)
    existing_yelp_ids = get_existing_scraped_yelp_ids()
    print(f"✅ Found {len(existing_yelp_ids)} existing restaurants in yelp_restaurants", flush=True)
    
    # Find missing restaurants (in queue but not in yelp_restaurants)
    missing_restaurants = []
    for queue_item in all_queue_restaurants:
        yelp_id = queue_item.get('yelp_id')
        if not yelp_id:
            # Try to extract from URL
            yelp_url = queue_item.get('url')
            if yelp_url:
                yelp_id = extract_yelp_id_from_url(yelp_url)
                if yelp_id:
                    queue_item['yelp_id'] = yelp_id
        
        if yelp_id and yelp_id not in existing_yelp_ids:
            missing_restaurants.append(queue_item)
    
    print(f"\n📊 Found {len(missing_restaurants)} restaurants in queue that are NOT in yelp_restaurants", flush=True)
    
    if not missing_restaurants:
        print("✅ All restaurants from queue are already in yelp_restaurants!", flush=True)
        return
    
    # Apply limit if specified
    if limit:
        missing_restaurants = missing_restaurants[:limit]
        print(f"📝 Processing {len(missing_restaurants)} restaurants (limit: {limit})", flush=True)
    
    # Setup browser
    brave_path = find_brave_path()
    if brave_path:
        print("✅ Brave browser found", flush=True)
    else:
        print("⚠️  Brave browser not found. Using system default...", flush=True)
    
    processed_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Check if running in CI environment
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    with sync_playwright() as p:
        launch_options = {
            "headless": headless,
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        }
        
        if is_ci:
            # In CI, use system Chromium
            launch_options["executable_path"] = "/usr/bin/chromium-browser"
            launch_options["args"].extend([
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--single-process'
            ])
        elif brave_path:
            launch_options["executable_path"] = brave_path
        
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            for i, queue_item in enumerate(missing_restaurants, 1):
                yelp_url = queue_item.get('url')
                yelp_id = queue_item.get('yelp_id') or extract_yelp_id_from_url(yelp_url)
                place_info = queue_item.get('lemon8_source', {}) or {}
                place_name = queue_item.get('place_name') or place_info.get('place_name', 'Unknown')
                
                print()
                print("="*60, flush=True)
                print(f"Restaurant {i}/{len(missing_restaurants)}: {place_name}", flush=True)
                print(f"Yelp ID: {yelp_id}", flush=True)
                print(f"URL: {yelp_url}", flush=True)
                print("="*60, flush=True)
                
                if not yelp_id:
                    print(f"⚠️  Could not extract Yelp ID from URL, skipping...", flush=True)
                    if queue_item.get('yelp_id'):
                        mark_yelp_url_failed(queue_item.get('yelp_id'), "Could not extract Yelp ID from URL")
                    failed_count += 1
                    continue
                
                # Double-check it's still not in database (race condition protection)
                if yelp_id in existing_yelp_ids:
                    print(f"⏭️  Already scraped (race condition), skipping...", flush=True)
                    skipped_count += 1
                    continue
                
                # Update queue status to processing
                mark_yelp_url_processing(yelp_id)
                
                try:
                    # Scrape restaurant detail
                    yelp_data = scrape_restaurant_detail(page, yelp_url, download_images_local=False)
                    
                    # Use place_name as fallback if Yelp name extraction failed
                    if not yelp_data.get("name"):
                        yelp_data["name"] = place_name
                        print(f"⚠️  Could not extract name from Yelp, using: {yelp_data['name']}", flush=True)
                    
                    # Convert to dict format
                    restaurant = convert_yelp_data_to_dict(yelp_data, place_info, yelp_id, yelp_url)
                    
                    # Save to Supabase yelp_restaurants table
                    success = save_yelp_restaurant_to_db(restaurant)
                    
                    if success:
                        # Update queue status to completed
                        mark_yelp_url_completed(yelp_id)
                        processed_count += 1
                        existing_yelp_ids.add(yelp_id)  # Add to local set to avoid duplicates
                        print(f"✅ Scraped and saved: {restaurant.get('name')}", flush=True)
                        print(f"   Rating: {restaurant.get('rating', 'N/A')}", flush=True)
                        print(f"   Reviews: {restaurant.get('total_reviews', 'N/A')}", flush=True)
                        print(f"   Address: {restaurant.get('address', 'N/A')[:50]}...", flush=True)
                        print(f"   Phone: {restaurant.get('phone', 'N/A')}", flush=True)
                        print(f"💾 Saved to Supabase: yelp_restaurants table", flush=True)
                    else:
                        print(f"⚠️  Scraped but failed to save to database", flush=True)
                        mark_yelp_url_failed(yelp_id, "Failed to save to database")
                        failed_count += 1
                    
                except Exception as e:
                    print(f"❌ Error scraping: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    sys.stdout.flush()
                    
                    # Update queue status to failed
                    mark_yelp_url_failed(yelp_id, str(e))
                    failed_count += 1
                
                # Delay between requests
                time.sleep(delay)
        
        finally:
            browser.close()
    
    # Final summary
    print()
    print("="*60, flush=True)
    print("📊 PROCESSING SUMMARY", flush=True)
    print("="*60, flush=True)
    print(f"✅ Processed: {processed_count}", flush=True)
    print(f"⏭️  Skipped (already scraped): {skipped_count}", flush=True)
    print(f"❌ Failed: {failed_count}", flush=True)
    print(f"📊 Total processed: {len(missing_restaurants)}", flush=True)
    print(f"💾 All data saved to Supabase:", flush=True)
    print(f"   - yelp_restaurants table (scraped restaurant data)", flush=True)
    print(f"   - crawl_queue_yelp table (queue status updated)", flush=True)
    
    # Show updated stats
    stats = get_yelp_queue_stats()
    if stats:
        print(f"\n📊 Updated Queue Stats:", flush=True)
        print(f"  Pending: {stats.get('pending', 0)}", flush=True)
        print(f"  Processing: {stats.get('processing', 0)}", flush=True)
        print(f"  Completed: {stats.get('completed', 0)}", flush=True)
        print(f"  Failed: {stats.get('failed', 0)}", flush=True)
    
    print("="*60, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process missing Yelp restaurants from queue')
    parser.add_argument('--limit', type=int, default=None, help='Number of restaurants to process (default: all missing)')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode (default: visible mode)')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between scraping operations in seconds')
    
    args = parser.parse_args()
    
    process_missing_restaurants(
        limit=args.limit,
        headless=args.headless,
        delay=args.delay
    )

