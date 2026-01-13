"""
Upload images from yelp_restaurants_from_lemon8.json to Supabase Storage

IMPORTANT: Run optimize_images.py first to resize and convert images to WebP format.
This significantly reduces bandwidth costs (Supabase Free Tier: 2GB/month).

Usage:
1. python optimize_images.py --input-dir restaurant_images
2. python upload_images_to_supabase.py --limit 10
"""
import json
import os
import sys
from typing import Dict, List
from supabase_config import (
    upload_image_to_storage, 
    upload_local_image_to_storage,
    upload_images_batch,
    get_supabase_client
)

# Force unbuffered output
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

print("=" * 60, flush=True)
print("IMAGE UPLOADER TO SUPABASE STORAGE", flush=True)
print("=" * 60, flush=True)


def process_restaurant_images(restaurant: Dict, bucket_name: str = "restaurant-images", 
                              use_local_paths: bool = True) -> Dict:
    """Process and upload all images for a restaurant"""
    yelp_id = restaurant.get("yelp_id", "unknown")
    restaurant_name = restaurant.get("name", "unknown")
    
    print(f"\n📤 Processing images for: {restaurant_name} ({yelp_id})", flush=True)
    
    uploaded_photos = []
    uploaded_image_urls = []
    
    # Collect all image sources
    image_sources = []
    
    # Check if we have local paths (from photo_miner_yelp.py)
    if use_local_paths:
        # First, try to find local images in restaurant_images folder
        safe_name = "".join(c for c in restaurant_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')[:50]
        restaurant_dir = os.path.join("restaurant_images", safe_name)
        
        if os.path.exists(restaurant_dir):
            # Found local directory, use those files
            # Prefer WebP files over original formats
            webp_files = []
            other_files = []
            
            for filename in sorted(os.listdir(restaurant_dir)):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    local_path = os.path.join(restaurant_dir, filename)
                    if os.path.exists(local_path):
                        if filename.lower().endswith('.webp'):
                            webp_files.append(("local", local_path))
                        else:
                            # Check if WebP version exists
                            webp_path = os.path.splitext(local_path)[0] + '.webp'
                            if os.path.exists(webp_path):
                                # WebP version exists, prefer that
                                if (webp_path, "local") not in [(f[1], f[0]) for f in webp_files]:
                                    webp_files.append(("local", webp_path))
                            else:
                                other_files.append(("local", local_path))
            
            # Add WebP files first (optimized), then other files
            image_sources.extend(webp_files)
            image_sources.extend(other_files)
        
        # Also check images field for local paths
        if restaurant.get("images"):
            for img in restaurant["images"]:
                if isinstance(img, str):
                    if os.path.exists(img):
                        image_sources.append(("local", img))
                    elif img.startswith("restaurant_images") and os.path.exists(img):
                        image_sources.append(("local", img))
        
        # Check photos field
        if restaurant.get("photos"):
            for photo in restaurant["photos"]:
                if isinstance(photo, str):
                    if os.path.exists(photo):
                        image_sources.append(("local", photo))
                    elif photo.startswith("restaurant_images") and os.path.exists(photo):
                        image_sources.append(("local", photo))
    
    # If no local paths found, use URLs
    if not image_sources:
        # Get photos URLs
        if restaurant.get("photos"):
            for photo in restaurant["photos"]:
                if isinstance(photo, str) and photo.startswith("http"):
                    image_sources.append(("url", photo))
        
        # Get images URLs
        if restaurant.get("images"):
            for img in restaurant["images"]:
                if isinstance(img, str) and img.startswith("http"):
                    image_sources.append(("url", img))
        
        # Get image_urls
        if restaurant.get("image_urls"):
            for img_url in restaurant["image_urls"]:
                if isinstance(img_url, str) and img_url.startswith("http"):
                    image_sources.append(("url", img_url))
    
    # Remove duplicates
    seen = set()
    unique_sources = []
    for source_type, source_path in image_sources:
        if source_path not in seen:
            seen.add(source_path)
            unique_sources.append((source_type, source_path))
    
    if not unique_sources:
        print(f"  ⚠️  No images found for this restaurant", flush=True)
        return restaurant
    
    print(f"  📊 Found {len(unique_sources)} unique images to upload", flush=True)
    
    # Upload images
    uploaded_count = 0
    failed_count = 0
    
    for idx, (source_type, source_path) in enumerate(unique_sources[:10], 1):  # Limit to 10 images per restaurant
        try:
            if source_type == "local":
                # Upload local file
                public_url = upload_local_image_to_storage(
                    source_path,
                    bucket_name=bucket_name,
                    folder="yelp",
                    yelp_id=yelp_id
                )
            else:
                # Upload from URL
                public_url = upload_image_to_storage(
                    source_path,
                    bucket_name=bucket_name,
                    folder="yelp",
                    yelp_id=yelp_id
                )
            
            if public_url:
                uploaded_photos.append(public_url)
                uploaded_image_urls.append(public_url)
                uploaded_count += 1
                print(f"    ✅ [{idx}/{len(unique_sources[:10])}] Uploaded", flush=True)
            else:
                failed_count += 1
                print(f"    ❌ [{idx}/{len(unique_sources[:10])}] Failed to upload", flush=True)
        except Exception as e:
            failed_count += 1
            print(f"    ⚠️  [{idx}/{len(unique_sources[:10])}] Error: {e}", flush=True)
    
    # Update restaurant data with Supabase URLs
    if uploaded_photos:
        restaurant["supabase_photos"] = uploaded_photos[:5]  # First 5 as main photos
        restaurant["supabase_image_urls"] = uploaded_image_urls
        restaurant["supabase_images"] = uploaded_image_urls  # Alias for compatibility
        
        # Update menu items with Supabase URLs (if they have images)
        if restaurant.get("menu_items"):
            for item in restaurant["menu_items"]:
                if item.get("images"):
                    item_supabase_urls = []
                    for img in item["images"][:3]:  # Limit to 3 per menu item
                        if isinstance(img, str):
                            if img.startswith("http"):
                                supabase_url = upload_image_to_storage(
                                    img,
                                    bucket_name=bucket_name,
                                    folder=f"yelp/{yelp_id}/menu",
                                    yelp_id=yelp_id
                                )
                                if supabase_url:
                                    item_supabase_urls.append(supabase_url)
                    if item_supabase_urls:
                        item["supabase_images"] = item_supabase_urls
        
        # Update popular dishes with Supabase URLs
        if restaurant.get("popular_dishes"):
            for dish in restaurant["popular_dishes"]:
                if dish.get("images"):
                    dish_supabase_urls = []
                    for img in dish["images"][:3]:  # Limit to 3 per dish
                        if isinstance(img, str):
                            if img.startswith("http"):
                                supabase_url = upload_image_to_storage(
                                    img,
                                    bucket_name=bucket_name,
                                    folder=f"yelp/{yelp_id}/dishes",
                                    yelp_id=yelp_id
                                )
                                if supabase_url:
                                    dish_supabase_urls.append(supabase_url)
                    if dish_supabase_urls:
                        dish["supabase_images"] = dish_supabase_urls
        
        print(f"  ✅ Uploaded {uploaded_count}/{len(unique_sources[:10])} images", flush=True)
        if failed_count > 0:
            print(f"  ⚠️  Failed: {failed_count} images", flush=True)
    else:
        print(f"  ❌ No images were successfully uploaded", flush=True)
    
    return restaurant


def upload_all_images(json_file: str = "yelp_restaurants_from_lemon8.json",
                     output_file: str = "yelp_restaurants_from_lemon8.json",
                     bucket_name: str = "restaurant-images",
                     limit: int = None,
                     use_local_paths: bool = True):
    """Upload all images from JSON file to Supabase Storage"""
    
    # Check Supabase connection
    print("🔍 Checking Supabase connection...", flush=True)
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to connect to Supabase!", flush=True)
        print("Make sure SUPABASE_URL and SUPABASE_KEY are set in environment variables.", flush=True)
        return
    
    print("✅ Connected to Supabase", flush=True)
    print()
    
    # Load JSON file
    print(f"📂 Loading {json_file}...", flush=True)
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}", flush=True)
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        restaurants = json.load(f)
    
    total_restaurants = len(restaurants)
    print(f"✅ Loaded {total_restaurants} restaurants", flush=True)
    
    if limit:
        restaurants = restaurants[:limit]
        print(f"📊 Processing first {limit} restaurants", flush=True)
    
    print()
    
    # Process each restaurant
    processed = 0
    failed = 0
    
    for idx, restaurant in enumerate(restaurants, 1):
        try:
            print(f"[{idx}/{len(restaurants)}] ", end="", flush=True)
            restaurant = process_restaurant_images(restaurant, bucket_name, use_local_paths)
            processed += 1
        except Exception as e:
            print(f"❌ Error processing restaurant: {e}", flush=True)
            failed += 1
            import traceback
            traceback.print_exc()
    
    # Save updated JSON
    print()
    print(f"💾 Saving updated data to {output_file}...", flush=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(restaurants, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 60, flush=True)
    print("UPLOAD SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"✅ Processed: {processed}", flush=True)
    print(f"❌ Failed: {failed}", flush=True)
    print(f"💾 Updated JSON saved to: {output_file}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload images to Supabase Storage")
    parser.add_argument("--json-file", default="yelp_restaurants_from_lemon8.json",
                       help="Input JSON file")
    parser.add_argument("--output-file", default="yelp_restaurants_from_lemon8.json",
                       help="Output JSON file (can be same as input)")
    parser.add_argument("--bucket", default="restaurant-images",
                       help="Supabase Storage bucket name")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of restaurants to process")
    parser.add_argument("--use-urls", action="store_true",
                       help="Force using URLs instead of local paths")
    
    args = parser.parse_args()
    
    upload_all_images(
        json_file=args.json_file,
        output_file=args.output_file,
        bucket_name=args.bucket,
        limit=args.limit,
        use_local_paths=not args.use_urls
    )

