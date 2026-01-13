"""
Link photos from Supabase Storage to places in lemon8_articles.itinerary_data

This script:
1. Queries lemon8_articles table for articles with itinerary_data
2. Extracts stops (places) from itinerary_data
3. Matches places with restaurants in yelp_restaurants_from_lemon8.json
4. Finds photos in Supabase Storage bucket
5. Updates itinerary_data with photo URLs for each stop
"""
import json
import os
import sys
from typing import Dict, List, Optional
from supabase_config import get_supabase_client, get_supabase_credentials
from difflib import SequenceMatcher

# Force unbuffered output
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

print("=" * 60, flush=True)
print("LINK PHOTOS TO ITINERARIES", flush=True)
print("=" * 60, flush=True)


def similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def load_restaurants_from_json(json_file: str = "yelp_restaurants_from_lemon8.json") -> Dict[str, Dict]:
    """Load restaurants from JSON file and create lookup dictionary"""
    if not os.path.exists(json_file):
        print(f"⚠️  JSON file not found: {json_file}", flush=True)
        return {}
    
    print(f"📂 Loading restaurants from {json_file}...", flush=True)
    with open(json_file, 'r', encoding='utf-8') as f:
        restaurants = json.load(f)
    
    # Create lookup dictionary: key = (name_lower, city_lower), value = restaurant data
    # Also create a list for fuzzy matching
    lookup = {}
    restaurant_list = []  # For fuzzy matching
    
    for restaurant in restaurants:
        name = restaurant.get("name", "").lower().strip()
        city = restaurant.get("city", "").lower().strip()
        yelp_id = restaurant.get("yelp_id", "")
        
        if name and yelp_id:
            # Multiple keys for exact matching
            key1 = (name, city)
            key2 = (name, "")  # Without city
            lookup[key1] = restaurant
            if key2 not in lookup:  # Don't overwrite if key1 exists
                lookup[key2] = restaurant
            
            # Also store in list for fuzzy matching
            restaurant_list.append({
                'name': name,
                'city': city,
                'restaurant': restaurant
            })
    
    # Store restaurant_list in lookup for fuzzy matching
    lookup['_restaurant_list'] = restaurant_list
    
    print(f"✅ Loaded {len(restaurants)} restaurants", flush=True)
    return lookup


def find_matching_restaurant(place_name: str, city: str, restaurants_lookup: Dict) -> Optional[Dict]:
    """Find matching restaurant by place name and city"""
    place_name_lower = place_name.lower().strip()
    city_lower = city.lower().strip()
    
    # Normalize place name (remove common suffixes)
    place_name_normalized = place_name_lower
    for suffix in ["'s", "'", " restaurant", " cafe", " coffee", " bar", " grill"]:
        if place_name_normalized.endswith(suffix):
            place_name_normalized = place_name_normalized[:-len(suffix)].strip()
    
    # Try exact match first
    key1 = (place_name_lower, city_lower)
    if key1 in restaurants_lookup:
        return restaurants_lookup[key1]
    
    # Try normalized name
    key1_norm = (place_name_normalized, city_lower)
    if key1_norm in restaurants_lookup:
        return restaurants_lookup[key1_norm]
    
    # Try without city
    key2 = (place_name_lower, "")
    if key2 in restaurants_lookup:
        return restaurants_lookup[key2]
    
    key2_norm = (place_name_normalized, "")
    if key2_norm in restaurants_lookup:
        return restaurants_lookup[key2_norm]
    
    # Try fuzzy matching with all restaurants
    best_match = None
    best_score = 0.0
    
    # Get restaurant list for fuzzy matching
    restaurant_list = restaurants_lookup.get('_restaurant_list', [])
    
    # If no list, iterate through lookup (excluding special keys)
    if not restaurant_list:
        for key, restaurant in restaurants_lookup.items():
            if key == '_restaurant_list':
                continue
            if not isinstance(key, tuple) or len(key) != 2:
                continue
            lookup_name, lookup_city = key
            # Continue with matching logic below
    else:
        # Use restaurant list
        for item in restaurant_list:
            lookup_name = item['name']
            lookup_city = item['city']
            restaurant = item['restaurant']
        # Calculate name similarity
        name_score = similarity(place_name_lower, lookup_name)
        name_score_norm = similarity(place_name_normalized, lookup_name)
        name_score = max(name_score, name_score_norm)
        
        # If city matches, boost the score
        city_match = False
        if city_lower and lookup_city:
            city_match = city_lower in lookup_city or lookup_city in city_lower
        elif not lookup_city:
            city_match = True  # No city in lookup, accept any
        
        if city_match:
            name_score *= 1.1
        
        # Lower threshold for better matching
        # Require higher similarity to avoid false matches
        # Also check if one name contains the other (for partial matches)
        contains_match = place_name_lower in lookup_name or lookup_name in place_name_lower
        
        if contains_match and len(place_name_lower) > 3 and len(lookup_name) > 3:
            # Boost score for contains match
            name_score = max(name_score, 0.85)
        
        if name_score > best_score and name_score > 0.75:  # 75% similarity threshold
            best_score = name_score
            best_match = restaurant
    
    return best_match


def get_photos_from_storage(yelp_id: str, bucket_name: str = "restaurant-images", 
                           folder: str = "yelp") -> List[str]:
    """Get photo URLs from Supabase Storage for a restaurant"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        # List files in the restaurant's folder
        storage_path = f"{folder}/{yelp_id}"
        files = supabase.storage.from_(bucket_name).list(storage_path)
        
        if not files:
            return []
        
        # Get public URLs for image files
        photo_urls = []
        for file_info in files:
            if isinstance(file_info, dict):
                filename = file_info.get("name", "")
            else:
                filename = str(file_info)
            
            # Filter for image files
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                # Get public URL
                file_path = f"{storage_path}/{filename}"
                public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
                photo_urls.append(public_url)
        
        return photo_urls[:5]  # Return first 5 photos
        
    except Exception as e:
        # Folder might not exist or no access
        return []


def get_photos_from_restaurant_data(restaurant: Dict) -> List[str]:
    """Extract photo URLs from restaurant data"""
    photos = []
    
    # Priority 1: Check supabase_photos (uploaded to Supabase Storage)
    if restaurant.get("supabase_photos"):
        photos.extend(restaurant["supabase_photos"])
    
    # Priority 2: Check supabase_image_urls
    if restaurant.get("supabase_image_urls"):
        photos.extend(restaurant["supabase_image_urls"])
    
    # Priority 3: Check supabase_images
    if restaurant.get("supabase_images"):
        photos.extend(restaurant["supabase_images"])
    
    # Priority 4: Fallback to original photos/image_urls (Yelp URLs)
    if not photos:
        if restaurant.get("photos"):
            photos.extend(restaurant["photos"])
        if restaurant.get("image_urls"):
            photos.extend(restaurant["image_urls"])
        if restaurant.get("images"):
            photos.extend(restaurant["images"])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_photos = []
    for photo in photos:
        if photo and photo not in seen:
            seen.add(photo)
            unique_photos.append(photo)
    
    return unique_photos[:5]  # Return first 5 photos


def link_photos_to_stop(stop: Dict, restaurants_lookup: Dict, 
                        bucket_name: str = "restaurant-images") -> Dict:
    """Link photos to a stop (place) in itinerary_data"""
    place_name = stop.get("place_name", "")
    city = stop.get("city", "")
    
    if not place_name:
        return stop
    
    # Find matching restaurant
    restaurant = find_matching_restaurant(place_name, city, restaurants_lookup)
    
    if not restaurant:
        return stop
    
    # Get photos
    photos = []
    
    # First, try to get from restaurant data (if already uploaded)
    photos = get_photos_from_restaurant_data(restaurant)
    
    # If no photos in data, try to get from storage
    if not photos:
        yelp_id = restaurant.get("yelp_id")
        if yelp_id:
            photos = get_photos_from_storage(yelp_id, bucket_name)
    
    # Add photos to stop
    if photos:
        stop["photos"] = photos
        stop["photo_count"] = len(photos)
        stop["yelp_id"] = restaurant.get("yelp_id")
        stop["matched_restaurant"] = restaurant.get("name")
    
    return stop


def update_article_with_photos(article_url: str, itinerary_data: Dict, 
                               restaurants_lookup: Dict,
                               bucket_name: str = "restaurant-images") -> bool:
    """Update article's itinerary_data with photo URLs"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    if not itinerary_data:
        return False
    
    stops = itinerary_data.get("stops", [])
    if not stops:
        return False
    
    # Link photos to each stop
    updated_stops = []
    photos_linked = 0
    
    for stop in stops:
        original_stop = stop.copy()
        updated_stop = link_photos_to_stop(stop, restaurants_lookup, bucket_name)
        
        if updated_stop.get("photos"):
            photos_linked += 1
        
        updated_stops.append(updated_stop)
    
    # Update itinerary_data
    itinerary_data["stops"] = updated_stops
    
    # Update database
    try:
        supabase.table("lemon8_articles")\
            .update({"itinerary_data": itinerary_data})\
            .eq("url", article_url)\
            .execute()
        
        return True
    except Exception as e:
        print(f"  ⚠️  Error updating article: {e}", flush=True)
        return False


def link_photos_to_all_articles(limit: Optional[int] = None,
                                bucket_name: str = "restaurant-images",
                                json_file: str = "yelp_restaurants_from_lemon8.json"):
    """Link photos to all articles in lemon8_articles table"""
    
    # Check Supabase connection
    print("🔍 Checking Supabase connection...", flush=True)
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to connect to Supabase!", flush=True)
        return
    
    print("✅ Connected to Supabase", flush=True)
    print()
    
    # Load restaurants lookup
    restaurants_lookup = load_restaurants_from_json(json_file)
    if not restaurants_lookup:
        print("⚠️  No restaurants loaded. Cannot link photos.", flush=True)
        return
    
    print()
    
    # Query articles
    print("📂 Querying lemon8_articles table...", flush=True)
    try:
        query = supabase.table("lemon8_articles")\
            .select("url, itinerary_data")\
            .not_.is_("itinerary_data", "null")
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        articles = response.data
        
        print(f"✅ Found {len(articles)} articles with itinerary_data", flush=True)
        print()
        
    except Exception as e:
        print(f"❌ Error querying articles: {e}", flush=True)
        return
    
    # Process each article
    processed = 0
    updated = 0
    photos_linked_total = 0
    
    for idx, article in enumerate(articles, 1):
        article_url = article.get("url", "")
        itinerary_data = article.get("itinerary_data")
        
        if not itinerary_data or not article_url:
            continue
        
        stops = itinerary_data.get("stops", [])
        if not stops:
            continue
        
        print(f"[{idx}/{len(articles)}] Processing: {article_url[:60]}...", flush=True)
        print(f"  📍 Found {len(stops)} stops", flush=True)
        
        # Debug: Show place names
        place_names = [stop.get("place_name", "") for stop in stops]
        print(f"  🏷️  Places: {', '.join(place_names[:3])}{'...' if len(place_names) > 3 else ''}", flush=True)
        
        # Count how many stops will get photos
        stops_with_photos = 0
        for stop in stops:
            place_name = stop.get("place_name", "")
            city = itinerary_data.get("city", "")
            restaurant = find_matching_restaurant(place_name, city, restaurants_lookup)
            if restaurant:
                print(f"    ✅ Matched: {place_name} → {restaurant.get('name')}", flush=True)
                photos = get_photos_from_restaurant_data(restaurant)
                if not photos:
                    yelp_id = restaurant.get("yelp_id")
                    if yelp_id:
                        photos = get_photos_from_storage(yelp_id, bucket_name)
                if photos:
                    stops_with_photos += 1
                    print(f"      📸 Found {len(photos)} photos", flush=True)
                else:
                    print(f"      ⚠️  No photos found for {restaurant.get('name')}", flush=True)
            else:
                print(f"    ❌ No match: {place_name}", flush=True)
        
        if stops_with_photos > 0:
            # Update article
            success = update_article_with_photos(article_url, itinerary_data, restaurants_lookup, bucket_name)
            if success:
                updated += 1
                photos_linked_total += stops_with_photos
                print(f"  ✅ Linked photos to {stops_with_photos}/{len(stops)} stops", flush=True)
            else:
                print(f"  ❌ Failed to update article", flush=True)
        else:
            print(f"  ⏭️  No matching restaurants found", flush=True)
        
        processed += 1
        print()
    
    # Summary
    print("=" * 60, flush=True)
    print("LINKING SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"✅ Processed: {processed} articles", flush=True)
    print(f"📸 Updated: {updated} articles", flush=True)
    print(f"🖼️  Photos linked: {photos_linked_total} stops", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Link photos to itinerary stops")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of articles to process")
    parser.add_argument("--bucket", default="restaurant-images",
                       help="Supabase Storage bucket name")
    parser.add_argument("--json-file", default="yelp_restaurants_from_lemon8.json",
                       help="JSON file with restaurant data")
    
    args = parser.parse_args()
    
    link_photos_to_all_articles(
        limit=args.limit,
        bucket_name=args.bucket,
        json_file=args.json_file
    )

