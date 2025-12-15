"""
Script to scrape Yelp restaurant data from Lemon8 articles and save to JSON.

Workflow:
1. Query Supabase lemon8_articles table for itinerary_data
2. Extract place_name from stops
3. Check if Yelp URL already exists in JSON (skip if found)
4. Find Yelp URLs using yelp_url_enricher (only for new restaurants)
5. Scrape Yelp pages using yelp_scraper
6. Save to JSON file (yelp_restaurants_from_lemon8.json)
"""

import os
import sys
import json
import time
import argparse
from typing import List, Dict, Optional
from urllib.parse import urlparse

from supabase_config import get_supabase_client
from yelp_url_enricher import find_yelp_url
from scrapers.yelp_scraper import scrape_restaurant_detail, find_brave_path
from playwright.sync_api import sync_playwright


def get_restaurants_from_lemon8_articles(limit: Optional[int] = None) -> List[Dict]:
    """
    Query Supabase lemon8_articles table and extract restaurant names from itinerary_data.
    
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
        print("ERROR: Could not connect to Supabase")
        return []
    
    try:
        # Query articles that have itinerary_data
        query = supabase.table("lemon8_articles")\
            .select("url, itinerary_data")\
            .not_.is_("itinerary_data", "null")
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        
        restaurants = []
        seen_places = set()  # Avoid duplicates
        
        for article in response.data:
            article_url = article.get("url")
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
        
        return restaurants
        
    except Exception as e:
        print(f"ERROR: Failed to query Supabase: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_yelp_id_from_url(url: str) -> Optional[str]:
    """Extract Yelp business ID from URL"""
    # Yelp URLs format: https://www.yelp.com/biz/restaurant-name-new-york
    # or: https://www.yelp.com/biz/restaurant-name-new-york?some=params
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'biz':
            # Return the business slug as source_id
            return path_parts[1]
    except:
        pass
    return None


def load_existing_scraped_data(json_file: str = "yelp_restaurants_from_lemon8.json") -> Dict:
    """Load existing scraped data from JSON file"""
    if not os.path.exists(json_file):
        return {}
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Convert list to dict keyed by yelp_id for easy lookup
            if isinstance(data, list):
                result = {}
                for item in data:
                    yelp_id = item.get('yelp_id') or extract_yelp_id_from_url(item.get('url', ''))
                    if yelp_id:
                        result[yelp_id] = item
                return result
            return data
    except Exception as e:
        print(f"⚠️  Error loading existing data: {e}")
        return {}


def save_scraped_data(scraped_data: List[Dict], json_file: str = "yelp_restaurants_from_lemon8.json"):
    """Save scraped data to JSON file"""
    # Load existing data
    existing_data = load_existing_scraped_data(json_file)
    
    # Merge new data with existing
    for item in scraped_data:
        yelp_id = item.get('yelp_id')
        if yelp_id:
            existing_data[yelp_id] = item
    
    # Convert back to list for JSON
    data_list = list(existing_data.values())
    
    # Save to file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved {len(data_list)} restaurants to {json_file}")


def convert_yelp_data_to_dict(yelp_data: Dict, place_info: Dict) -> Dict:
    """
    Convert scraped Yelp data to ScrapedRestaurant model instance.
    
    Args:
        yelp_data: Dictionary from scrape_restaurant_detail
        place_info: Original place info from Lemon8 (for fallback data)
    
    Returns:
        ScrapedRestaurant instance (not saved yet)
    """
    url = yelp_data.get("url", "")
    yelp_id = extract_yelp_id_from_url(url) or url.split('/')[-1].split('?')[0]
    
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
        # If hours is a string, try to parse it
        hours_str = yelp_data.get("hours")
        if isinstance(hours_str, str):
            # Simple parsing - could be improved
            hours = {"raw": hours_str}
        elif isinstance(hours_str, dict):
            hours = hours_str
    
    # Extract photos
    photos = []
    if yelp_data.get("image_urls"):
        photos = yelp_data.get("image_urls", [])
    elif yelp_data.get("images"):
        # If images are local paths, we might want to keep URLs instead
        photos = yelp_data.get("images", [])
    
    # Extract popular dishes
    menu_items = []
    if yelp_data.get("popular_dishes"):
        for dish in yelp_data.get("popular_dishes", []):
            menu_items.append({
                "name": dish.get("name", ""),
                "images": dish.get("images", [])
            })
    
    # Create dictionary (instead of model)
    restaurant = {
        "source": "yelp",
        "yelp_id": yelp_id,
        "source_id": yelp_id,
        "source_url": url,
        "url": url,
        "name": yelp_data.get("name") or place_info.get("place_name", "Unknown"),
        "description": yelp_data.get("description", ""),
        "address": address or f"{city}, {state}",
        "city": city,
        "state": state,
        "rating": float(yelp_data.get("rating")) if yelp_data.get("rating") else None,
        "total_reviews": int(yelp_data.get("review_count", 0)) if yelp_data.get("review_count") else 0,
        "review_count": int(yelp_data.get("review_count", 0)) if yelp_data.get("review_count") else 0,
        "price_range": (yelp_data.get("price_range", "") or "")[:10],  # Truncate to max 10 chars
        "phone": yelp_data.get("phone", ""),
        "website": yelp_data.get("website", ""),
        "hours": hours,
        "categories": categories,
        "cuisine": yelp_data.get("cuisine", ""),
        "photos": photos,
        "images": yelp_data.get("images", []),
        "image_urls": yelp_data.get("image_urls", []),
        "menu_items": menu_items,
        "popular_dishes": yelp_data.get("popular_dishes", []),
        "reviews": yelp_data.get("reviews", [])[:5],  # Store first 5 reviews
        "menu_link": yelp_data.get("menu_link", ""),
        "amenities": yelp_data.get("amenities", []),
        "location": yelp_data.get("location", {}),
        "lemon8_source": place_info,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return restaurant


def scrape_and_save_yelp_restaurants(
    limit: Optional[int] = None,
    headless: bool = True,
    delay: float = 2.0,
    skip_existing: bool = True,
    json_file: str = "yelp_restaurants_from_lemon8.json"
):
    """
    Main function to scrape Yelp restaurants from Lemon8 articles and save to JSON.
    
    Args:
        limit: Limit number of Lemon8 articles to process
        headless: Run browser in headless mode
        delay: Delay between scraping operations
        skip_existing: Skip restaurants that already exist in JSON file
        json_file: Output JSON file path
    """
    print("="*60)
    print("🍽️  YELP SCRAPING FROM LEMON8 ARTICLES")
    print("="*60)
    print()
    
    # Step 1: Load existing scraped data
    print("📂 Step 1: Loading existing scraped data...")
    existing_data = load_existing_scraped_data(json_file)
    existing_yelp_ids = set(existing_data.keys())
    existing_yelp_urls = {item.get('url', ''): item for item in existing_data.values() if item.get('url')}
    print(f"✅ Found {len(existing_data)} existing restaurants in {json_file}")
    print()
    
    # Step 2: Get restaurants from Lemon8 articles
    print("📋 Step 2: Querying Supabase for restaurants from Lemon8 articles...")
    restaurants_to_enrich = get_restaurants_from_lemon8_articles(limit=limit)
    print(f"✅ Found {len(restaurants_to_enrich)} unique restaurants")
    print()
    
    if not restaurants_to_enrich:
        print("❌ No restaurants found to enrich.")
        return
    
    # Step 3: Find Yelp URLs (only for restaurants not already scraped)
    print("🔍 Step 3: Finding Yelp URLs (skipping already scraped)...")
    yelp_urls = {}
    found_count = 0
    skipped_count = 0
    
    for i, restaurant in enumerate(restaurants_to_enrich, 1):
        place_name = restaurant['place_name']
        city = restaurant['city']
        
        # Check if we already have a Yelp URL for this restaurant
        # First check by place_name + city in existing data
        already_scraped = False
        for existing_item in existing_data.values():
            lemon8_source = existing_item.get('lemon8_source', {})
            if (lemon8_source.get('place_name') == place_name and 
                lemon8_source.get('city') == city):
                yelp_url = existing_item.get('url') or existing_item.get('source_url')
                if yelp_url:
                    yelp_urls[place_name] = {
                        'url': yelp_url,
                        'place_info': restaurant,
                        'already_scraped': True
                    }
                    already_scraped = True
                    skipped_count += 1
                    print(f"  [{i}/{len(restaurants_to_enrich)}] {place_name} ({city}): ⏭️  Already scraped")
                    break
        
        if already_scraped:
            continue
        
        # Need to find Yelp URL
        print(f"  [{i}/{len(restaurants_to_enrich)}] Searching for: {place_name} ({city})")
        
        yelp_url = find_yelp_url(place_name, city, headless=headless)
        
        if yelp_url:
            yelp_id = extract_yelp_id_from_url(yelp_url)
            # Check if this Yelp URL is already in our data
            if skip_existing and yelp_id and yelp_id in existing_yelp_ids:
                skipped_count += 1
                print(f"    ⏭️  Yelp URL already scraped: {yelp_url}")
            else:
                yelp_urls[place_name] = {
                    'url': yelp_url,
                    'place_info': restaurant,
                    'already_scraped': False
                }
                found_count += 1
                print(f"    ✅ Found: {yelp_url}")
        else:
            print(f"    ❌ Not found")
        
        time.sleep(delay)
    
    print(f"\n✅ Found {found_count} new Yelp URLs, skipped {skipped_count} already scraped")
    print()
    
    if not yelp_urls:
        print("❌ No new Yelp URLs to scrape. Exiting.")
        return
    
    # Step 4: Filter out already scraped URLs
    new_yelp_urls = {k: v for k, v in yelp_urls.items() if not v.get('already_scraped', False)}
    
    if not new_yelp_urls:
        print("⏭️  All restaurants already scraped. Exiting.")
        return
    
    print(f"📥 Step 4: Scraping {len(new_yelp_urls)} new Yelp restaurant pages...")
    print()
    
    # Step 4: Scrape Yelp pages (collect data first, save later)
    print("📥 Step 4: Scraping Yelp restaurant pages...")
    
    brave_path = find_brave_path()
    if not brave_path:
        print("⚠️  Brave browser not found. Using system default...")
    
    scraped_data = []  # Collect all scraped data first
    
    with sync_playwright() as p:
        launch_options = {
            "headless": headless,
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        }
        
        if brave_path:
            launch_options["executable_path"] = brave_path
        
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            for i, (place_name, data) in enumerate(yelp_urls.items(), 1):
                yelp_url = data['url']
                place_info = data['place_info']
                yelp_id = extract_yelp_id_from_url(yelp_url)
                
                print()
                print("="*60)
                print(f"Restaurant {i}/{len(yelp_urls)}: {place_name}")
                print(f"URL: {yelp_url}")
                print("="*60)
                
                # Check if already exists (using pre-checked set)
                if skip_existing and yelp_id and yelp_id in existing_ids:
                    print(f"⏭️  Already exists in database, skipping...")
                    continue
                
                try:
                    # Scrape restaurant detail
                    yelp_data = scrape_restaurant_detail(page, yelp_url, download_images_local=False)
                    
                    # Use place_name as fallback if Yelp name extraction failed
                    if not yelp_data.get("name"):
                        yelp_data["name"] = place_info.get("place_name", "Unknown Restaurant")
                        print(f"⚠️  Could not extract name from Yelp, using: {yelp_data['name']}")
                    
                    # Store data for later saving
                    scraped_data.append({
                        'yelp_data': yelp_data,
                        'place_info': place_info,
                        'yelp_id': yelp_id
                    })
                    
                    print(f"✅ Scraped: {yelp_data.get('name')}")
                    print(f"   Rating: {yelp_data.get('rating', 'N/A')}")
                    print(f"   Reviews: {yelp_data.get('review_count', 'N/A')}")
                    
                except Exception as e:
                    print(f"❌ Error scraping: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Delay between requests
                time.sleep(delay)
        
        finally:
            browser.close()
    
    # Step 5: Save to database (outside Playwright context)
    print()
    print("💾 Step 5: Saving to database...")
    saved_count = 0
    skipped_count = len(existing_ids)
    failed_count = 0
    
    for item in scraped_data:
        try:
            yelp_data = item['yelp_data']
            place_info = item['place_info']
            yelp_id = item['yelp_id']
            
            # Check if exists and update or create
            yelp_id = item['yelp_id']
            existing = None
            if yelp_id:
                existing = ScrapedRestaurant.objects.filter(
                    source='yelp',
                    source_id=yelp_id
                ).first()
            
            # Convert to model
            restaurant = convert_yelp_data_to_model(yelp_data, place_info)
            
            if existing:
                if skip_existing:
                    skipped_count += 1
                    print(f"⏭️  Skipped (exists): {restaurant.name}")
                    continue
                else:
                    # Update existing
                    for field in ['name', 'rating', 'total_reviews', 'address', 'phone', 'website', 
                                 'price_range', 'hours', 'categories', 'photos', 'menu_items', 'raw_data']:
                        if hasattr(restaurant, field):
                            setattr(existing, field, getattr(restaurant, field))
                    existing.save()
                    saved_count += 1
                    print(f"✅ Updated: {restaurant.name}")
            else:
                # Create new
                restaurant.save()
                saved_count += 1
                print(f"✅ Saved: {restaurant.name}")
            
        except Exception as e:
            print(f"❌ Error saving: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
    
    # Final summary
    print()
    print("="*60)
    print("📊 SCRAPING SUMMARY")
    print("="*60)
    print(f"✅ Saved: {saved_count}")
    print(f"⏭️  Skipped (existing): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Total processed: {len(yelp_urls)}")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape Yelp restaurants from Lemon8 articles')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of Lemon8 articles to process')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between operations in seconds')
    parser.add_argument('--no-skip', action='store_true', help='Do not skip existing restaurants')
    
    args = parser.parse_args()
    
    scrape_and_save_yelp_restaurants(
        limit=args.limit,
        headless=not args.visible,
        delay=args.delay,
        skip_existing=not args.no_skip
    )

