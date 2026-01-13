"""
Script to download images from existing URLs in yelp_restaurant_details.json
Uses Playwright with proper headers to avoid Access Denied errors
"""

from playwright.sync_api import sync_playwright
import json
import os
from pathlib import Path
from urllib.parse import urlparse

def find_brave_path():
    """Find Brave browser executable path"""
    possible_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def download_image_with_page(page, image_url: str, save_path: str) -> bool:
    """Download an image using page's request context (with proper headers/cookies from Yelp session)"""
    try:
        # Use the page's request context which has all cookies and headers from Yelp
        response = page.request.get(
            image_url,
            timeout=30000,
            headers={
                'Referer': page.url,
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            }
        )
        
        if response.status == 200:
            body = response.body()
            
            # Check if response is valid (not an error page)
            if len(body) < 1000:
                print(f"      ⚠️  Response too small ({len(body)} bytes), might be error")
                return False
            
            with open(save_path, 'wb') as f:
                f.write(body)
            return True
        else:
            print(f"      ⚠️  Failed to download: Status {response.status}")
            return False
    except Exception as e:
        print(f"      ⚠️  Error downloading: {e}")
        return False

def download_images_from_json(json_file: str = "yelp_restaurants_from_lemon8.json", images_dir: str = "restaurant_images", limit: int = None):
    """Download all images from URLs in the JSON file"""
    
    # Load JSON file
    print("📂 Loading restaurant data...")
    with open(json_file, 'r', encoding='utf-8') as f:
        restaurants = json.load(f)
    
    total_restaurants = len(restaurants)
    
    # Apply limit if specified
    if limit:
        restaurants = restaurants[:limit]
        print(f"✅ Loaded {len(restaurants)} restaurants (limited from {total_restaurants})")
    else:
        print(f"✅ Loaded {len(restaurants)} restaurants")
    print()
    
    # Create images directory
    images_path = Path(images_dir)
    images_path.mkdir(exist_ok=True)
    
    # Find Brave browser
    brave_path = find_brave_path()
    if not brave_path:
        print("⚠️  Brave browser not found. Using system default...")
        brave_path = None
    
    # Statistics
    total_images = 0
    downloaded_images = 0
    failed_images = 0
    
    with sync_playwright() as p:
        print("🚀 Starting browser...")
        
        launch_options = {
            "headless": False,
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
            # First, navigate to Yelp to establish session
            print("🌐 Establishing Yelp session...")
            page.goto("https://www.yelp.com", wait_until="load", timeout=30000)
            print("✅ Session established")
            print()
            
            # Process each restaurant
            for idx, restaurant in enumerate(restaurants, 1):
                restaurant_name = restaurant.get("name", f"restaurant_{idx}")
                restaurant_url = restaurant.get("url", "")
                
                print("="*60)
                print(f"Restaurant {idx}/{len(restaurants)}: {restaurant_name}")
                print("="*60)
                
                # Extract images from all fields: photos, images, menu_items, popular_dishes
                all_image_urls = []
                image_mapping = {}  # Maps URL to (field_name, index) for updating JSON later
                
                # Get photos
                photos = restaurant.get("photos", [])
                for idx, photo_url in enumerate(photos):
                    if isinstance(photo_url, str) and photo_url.startswith("http"):
                        all_image_urls.append(photo_url)
                        image_mapping[photo_url] = ("photos", idx)
                
                # Get images
                images = restaurant.get("images", [])
                for idx, img_url in enumerate(images):
                    if isinstance(img_url, str) and img_url.startswith("http"):
                        all_image_urls.append(img_url)
                        if img_url not in image_mapping:  # Don't overwrite if already in photos
                            image_mapping[img_url] = ("images", idx)
                
                # Get menu_items images
                menu_items = restaurant.get("menu_items", [])
                for item_idx, item in enumerate(menu_items):
                    if isinstance(item, dict):
                        item_images = item.get("images", [])
                        for img_idx, img_url in enumerate(item_images):
                            if isinstance(img_url, str) and img_url.startswith("http"):
                                all_image_urls.append(img_url)
                                if img_url not in image_mapping:
                                    image_mapping[img_url] = ("menu_items", item_idx, img_idx)
                
                # Get popular_dishes images
                popular_dishes = restaurant.get("popular_dishes", [])
                for dish_idx, dish in enumerate(popular_dishes):
                    if isinstance(dish, dict):
                        dish_images = dish.get("images", [])
                        for img_idx, img_url in enumerate(dish_images):
                            if isinstance(img_url, str) and img_url.startswith("http"):
                                all_image_urls.append(img_url)
                                if img_url not in image_mapping:
                                    image_mapping[img_url] = ("popular_dishes", dish_idx, img_idx)
                
                # Remove duplicates while preserving order
                seen_urls = set()
                unique_image_urls = []
                for url in all_image_urls:
                    if url not in seen_urls:
                        seen_urls.add(url)
                        unique_image_urls.append(url)
                
                # Create restaurant-specific directory
                safe_name = "".join(c for c in restaurant_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_name = safe_name.replace(' ', '_')[:50]
                restaurant_dir = images_path / safe_name
                restaurant_dir.mkdir(exist_ok=True)
                
                # Filter out already downloaded images (check if path exists)
                images_to_download = []
                url_to_local_path = {}  # Maps URL to local path for updating JSON
                local_paths = []  # Track all local paths for this restaurant
                
                for img_url in unique_image_urls:
                    # Check if it's already a local path in JSON
                    if isinstance(img_url, str) and (img_url.startswith(images_dir) or os.path.exists(img_url)):
                        url_to_local_path[img_url] = img_url
                        local_paths.append(img_url)
                        continue
                    
                    # It's a URL, need to download
                    if img_url.startswith("http"):
                        images_to_download.append(img_url)
                        total_images += 1
                
                if not images_to_download:
                    if local_paths:
                        print(f"    ✅ All images already downloaded ({len(local_paths)} images)")
                    else:
                        print(f"    ⚠️  No images found")
                    continue
                
                num_images_to_download = len(images_to_download)
                # Store original URLs before potentially replacing with page URLs
                original_urls = list(images_to_download)
                print(f"    📥 Downloading {num_images_to_download} images...")
                
                # Navigate to restaurant page to get proper cookies/headers and extract fresh image URLs
                page_image_urls = []
                if restaurant_url:
                    try:
                        page.goto(restaurant_url, wait_until="load", timeout=60000)
                        print(f"    ✅ Loaded restaurant page")
                        
                        # Wait for images to load
                        page.wait_for_timeout(3000)
                        
                        # Extract actual image URLs from the page (they may be different/updated)
                        print(f"    🔍 Extracting image URLs from page...")
                        page_image_urls = page.evaluate("""
                            () => {
                                const images = [];
                                // Find all image elements in photo galleries
                                const photoSelectors = [
                                    'img[src*="bphoto"]',
                                    'img[src*="yelpcdn.com"]',
                                    '.photo-box img',
                                    '[data-testid*="photo"] img',
                                    '.media-stream img'
                                ];
                                
                                for (const selector of photoSelectors) {
                                    document.querySelectorAll(selector).forEach(img => {
                                        const src = img.src || img.getAttribute('data-src') || img.getAttribute('srcset');
                                        if (src && src.includes('yelpcdn.com') && !images.includes(src)) {
                                            images.push(src);
                                        }
                                    });
                                }
                                
                                // Also try to get from background images
                                document.querySelectorAll('[style*="background-image"]').forEach(el => {
                                    const style = el.getAttribute('style');
                                    const match = style.match(/url\\(['"]?([^'")]+)['"]?\\)/);
                                    if (match && match[1].includes('yelpcdn.com')) {
                                        const url = match[1];
                                        if (!images.includes(url)) {
                                            images.push(url);
                                        }
                                    }
                                });
                                
                                return [...new Set(images)].slice(0, 20); // Return up to 20 unique URLs
                            }
                        """)
                        
                        if page_image_urls:
                            print(f"    ✅ Found {len(page_image_urls)} image URLs on page")
                            # Use page URLs if available, otherwise fall back to JSON URLs
                            images_to_download = page_image_urls[:num_images_to_download]
                        else:
                            print(f"    ⚠️  Could not extract URLs from page, using JSON URLs")
                            # Keep original images_to_download list
                    except Exception as e:
                        print(f"    ⚠️  Could not load restaurant page: {e}, using JSON URLs...")
                
                # Download each image
                for i, img_url in enumerate(images_to_download, 1):
                    try:
                        # Get file extension
                        parsed = urlparse(img_url)
                        ext = os.path.splitext(parsed.path)[1] or '.jpg'
                        if '?' in ext:
                            ext = ext.split('?')[0]
                        
                        # Create filename with index
                        filename = f"{i:03d}_{safe_name}{ext}"
                        filepath = restaurant_dir / filename
                        
                        # Skip if already downloaded
                        if filepath.exists():
                            relative_path = f"{images_dir}/{safe_name}/{filename}"
                            url_to_local_path[img_url] = relative_path
                            local_paths.append(relative_path)
                            print(f"      ⏭️  Already exists: {filename}")
                            continue
                        
                        # Download image
                        if download_image_with_page(page, img_url, str(filepath)):
                            # Store relative path for JSON update
                            relative_path = f"{images_dir}/{safe_name}/{filename}"
                            url_to_local_path[img_url] = relative_path
                            local_paths.append(relative_path)
                            downloaded_images += 1
                            print(f"      ✅ Downloaded: {filename}")
                        else:
                            failed_images += 1
                            print(f"      ❌ Failed: {filename}")
                    except Exception as e:
                        failed_images += 1
                        print(f"      ⚠️  Error downloading image {i}: {e}")
                
                # Update restaurant JSON with local paths in all image fields
                if url_to_local_path:
                    # Update main images array
                    if "images" in restaurant:
                        updated_images = []
                        for img in restaurant["images"]:
                            if isinstance(img, str):
                                if img.startswith("http") and img in url_to_local_path:
                                    updated_images.append(url_to_local_path[img])
                                elif img.startswith(images_dir) or os.path.exists(img):
                                    updated_images.append(img)
                                else:
                                    updated_images.append(img)
                        restaurant["images"] = updated_images
                    
                    # Update photos array
                    if "photos" in restaurant:
                        updated_photos = []
                        for photo in restaurant["photos"]:
                            if isinstance(photo, str):
                                if photo.startswith("http") and photo in url_to_local_path:
                                    updated_photos.append(url_to_local_path[photo])
                                elif photo.startswith(images_dir) or os.path.exists(photo):
                                    updated_photos.append(photo)
                                else:
                                    updated_photos.append(photo)
                        restaurant["photos"] = updated_photos
                    
                    # Update menu_items images
                    if "menu_items" in restaurant:
                        for item in restaurant["menu_items"]:
                            if isinstance(item, dict) and "images" in item:
                                updated_item_images = []
                                for img in item["images"]:
                                    if isinstance(img, str):
                                        if img.startswith("http") and img in url_to_local_path:
                                            updated_item_images.append(url_to_local_path[img])
                                        elif img.startswith(images_dir) or os.path.exists(img):
                                            updated_item_images.append(img)
                                        else:
                                            updated_item_images.append(img)
                                item["images"] = updated_item_images
                    
                    # Update popular_dishes images
                    if "popular_dishes" in restaurant:
                        for dish in restaurant["popular_dishes"]:
                            if isinstance(dish, dict) and "images" in dish:
                                updated_dish_images = []
                                for img in dish["images"]:
                                    if isinstance(img, str):
                                        if img.startswith("http") and img in url_to_local_path:
                                            updated_dish_images.append(url_to_local_path[img])
                                        elif img.startswith(images_dir) or os.path.exists(img):
                                            updated_dish_images.append(img)
                                        else:
                                            updated_dish_images.append(img)
                                dish["images"] = updated_dish_images
                    
                    # Keep original URLs as backup
                    if original_urls:
                        restaurant["image_urls"] = original_urls
                    
                    print(f"    ✅ Updated JSON with {len(url_to_local_path)} local image paths")
                
                # Save JSON after each restaurant
                try:
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(restaurants, f, indent=2, ensure_ascii=False)
                    print(f"    💾 Updated JSON file")
                except Exception as e:
                    print(f"    ⚠️  Error saving JSON: {e}")
                
                print()
        
        finally:
            browser.close()
    
    # Final summary
    print()
    print("="*60)
    print("📊 DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total images to download: {total_images}")
    print(f"✅ Successfully downloaded: {downloaded_images}")
    print(f"❌ Failed: {failed_images}")
    print(f"📁 Images saved to: {images_dir}")
    print("="*60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download images from Yelp restaurants JSON file")
    parser.add_argument("--json-file", default="yelp_restaurants_from_lemon8.json",
                       help="Input JSON file path")
    parser.add_argument("--images-dir", default="restaurant_images",
                       help="Directory to save images")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of restaurants to process")
    
    args = parser.parse_args()
    
    download_images_from_json(
        json_file=args.json_file,
        images_dir=args.images_dir,
        limit=args.limit
    )

