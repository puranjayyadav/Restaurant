"""
Download images from Yelp and upload to Supabase Storage for restaurants in yelp_restaurants table.

This script:
1. Queries yelp_restaurants table from Supabase
2. Downloads images from Yelp URLs using Playwright (like photo_miner_yelp.py)
3. Uploads images to Supabase Storage bucket
4. Updates yelp_restaurants table with Supabase Storage URLs
"""
import os
import sys
import time
import argparse
from typing import List, Dict, Optional
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# Force unbuffered output
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

print("=" * 60, flush=True)
print("DOWNLOAD & UPLOAD YELP IMAGES TO SUPABASE", flush=True)
print("=" * 60, flush=True)

from supabase_config import (
    get_supabase_client,
    upload_local_image_to_storage,
    upload_image_to_storage
)

# Import HeaderSelector (optional - will work without it)
HEADER_SELECTOR_AVAILABLE = False
try:
    from header_selector import HeaderSelector
    HEADER_SELECTOR_AVAILABLE = True
except ImportError as e:
    HEADER_SELECTOR_AVAILABLE = False
    # Don't print here to avoid encoding issues, will print later if needed
    pass
except Exception as e:
    HEADER_SELECTOR_AVAILABLE = False
    pass


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
                print(f"      [WARNING] Response too small ({len(body)} bytes), might be error", flush=True)
                return False
            
            with open(save_path, 'wb') as f:
                f.write(body)
            return True
        else:
            print(f"      [WARNING] Failed to download: Status {response.status}", flush=True)
            return False
    except Exception as e:
        print(f"      [WARNING] Error downloading: {e}", flush=True)
        return False


def get_restaurants_from_supabase(limit: Optional[int] = None, yelp_id: Optional[str] = None, 
                                 allow_reprocess: bool = False) -> List[Dict]:
    """Get restaurants from yelp_restaurants table that need image processing"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        query = supabase.table("yelp_restaurants").select("*")
        
        if yelp_id:
            query = query.eq("yelp_id", yelp_id)
        else:
            # Get restaurants that have photos but might not have Supabase URLs yet
            # We'll check if photos exist and are Yelp URLs (not Supabase URLs)
            query = query.not_.is_("photos", "null")
        
        query = query.order("scraped_at", desc=False)
        
        # Get all results first (or up to a reasonable limit for filtering)
        fetch_limit = limit * 3 if limit else 1000  # Fetch more to account for filtering
        query = query.limit(fetch_limit)
        
        result = query.execute()
        restaurants = result.data if result.data else []
        
        # If allow_reprocess is True, skip filtering and return all
        if allow_reprocess:
            if limit:
                restaurants = restaurants[:limit]
            return restaurants
        
        # Filter out restaurants that already have Supabase Storage URLs
        filtered_restaurants = []
        skipped_count = 0
        for restaurant in restaurants:
            # Check if already processed (has Supabase Storage URLs)
            already_processed = False
            
            # Check supabase_photos column
            supabase_photos = restaurant.get("supabase_photos")
            if supabase_photos and isinstance(supabase_photos, list) and len(supabase_photos) > 0:
                # Check if any URL is a Supabase URL
                if any("supabase.co" in str(url) for url in supabase_photos if url):
                    already_processed = True
            
            # Check supabase_image_urls column
            if not already_processed:
                supabase_image_urls = restaurant.get("supabase_image_urls")
                if supabase_image_urls and isinstance(supabase_image_urls, list) and len(supabase_image_urls) > 0:
                    if any("supabase.co" in str(url) for url in supabase_image_urls if url):
                        already_processed = True
            
            # Check supabase_images column
            if not already_processed:
                supabase_images = restaurant.get("supabase_images")
                if supabase_images and isinstance(supabase_images, list) and len(supabase_images) > 0:
                    if any("supabase.co" in str(url) for url in supabase_images if url):
                        already_processed = True
            
            # Also check if photos column already contains Supabase URLs (backward compatibility)
            # The update function replaces photos with Supabase URLs, so if any photo is Supabase, it's processed
            if not already_processed:
                photos = restaurant.get("photos")
                if photos and isinstance(photos, list) and len(photos) > 0:
                    # If any photo is a Supabase URL, the restaurant has been processed
                    has_supabase = any("supabase.co" in str(url) for url in photos if url)
                    if has_supabase:
                        already_processed = True
            
            if not already_processed:
                filtered_restaurants.append(restaurant)
                if limit and len(filtered_restaurants) >= limit:
                    break
            else:
                skipped_count += 1
        
        if skipped_count > 0:
            print(f"[SKIP] Skipped {skipped_count} already-processed restaurant(s)", flush=True)
        
        return filtered_restaurants
    except Exception as e:
        print(f"[WARNING] Error querying restaurants: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return []


def update_restaurant_with_photos_and_menu(yelp_id: str, supabase_photos: List[str], 
                                          supabase_image_urls: List[str],
                                          menu_items: List[Dict] = None,
                                          popular_dishes: List[Dict] = None,
                                          header_image_url: Optional[str] = None) -> bool:
    """Update restaurant record with Supabase Storage photo URLs and menu items"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Update existing columns with Supabase Storage URLs
        # This replaces the Yelp URLs with Supabase Storage URLs
        update_data = {
            "photos": supabase_photos,  # Update photos with Supabase URLs
            "images": supabase_photos,  # Also update images
            "image_urls": supabase_photos  # And image_urls
        }
        
        # Update menu_items if provided
        if menu_items is not None:
            update_data["menu_items"] = menu_items
        
        # Update popular_dishes if provided
        if popular_dishes is not None:
            update_data["popular_dishes"] = popular_dishes
        
        # First, update the basic fields (photos, images, menu_items, popular_dishes)
        try:
            # Try with supabase_photos columns if they exist
            test_update = update_data.copy()
            test_update["supabase_photos"] = supabase_photos
            test_update["supabase_image_urls"] = supabase_image_urls
            test_update["supabase_images"] = supabase_image_urls
            
            supabase.table("yelp_restaurants")\
                .update(test_update)\
                .eq("yelp_id", yelp_id)\
                .execute()
        except:
            # If supabase_photos columns don't exist, just update basic fields
            supabase.table("yelp_restaurants")\
                .update(update_data)\
                .eq("yelp_id", yelp_id)\
                .execute()
        
        # Then, try to update header_image_url separately (if provided)
        if header_image_url:
            try:
                supabase.table("yelp_restaurants")\
                    .update({"header_image_url": header_image_url})\
                    .eq("yelp_id", yelp_id)\
                    .execute()
            except Exception as header_error:
                # If header_image_url column doesn't exist or schema cache issue, just log it
                error_dict = header_error.args[0] if header_error.args and isinstance(header_error.args[0], dict) else {}
                error_code = error_dict.get("code", "")
                if "PGRST204" in error_code or "header_image_url" in str(header_error):
                    print(f"  [INFO] Could not update header_image_url (column may not be in schema cache yet)", flush=True)
                else:
                    print(f"  [WARNING] Error updating header_image_url: {header_error}", flush=True)
        
        return True
    except Exception as e:
        print(f"[WARNING] Error updating restaurant: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def parse_json_field(field_value):
    """Helper function to parse JSON strings"""
    if isinstance(field_value, str):
        import json
        try:
            return json.loads(field_value)
        except:
            return []
    return field_value if field_value else []


def process_restaurant_images(restaurant: Dict, page, bucket_name: str = "restaurant-images",
                             temp_dir: str = "temp_images") -> Dict:
    """Download images from Yelp and upload to Supabase Storage"""
    yelp_id = restaurant.get("yelp_id", "unknown")
    restaurant_name = restaurant.get("name", "unknown")
    restaurant_url = restaurant.get("url", "")
    
    print(f"\n[PROCESSING] Processing: {restaurant_name} ({yelp_id})", flush=True)
    
    # Collect all image URLs from all sources
    all_image_urls = []
    
    # 1. Get photos
    photos = parse_json_field(restaurant.get("photos", []))
    for photo in photos:
        if isinstance(photo, str) and photo.startswith("http"):
            all_image_urls.append(photo)
    
    # 2. Get images
    images = parse_json_field(restaurant.get("images", []))
    for img in images:
        if isinstance(img, str) and img.startswith("http"):
            all_image_urls.append(img)
    
    # 3. Get image_urls
    image_urls = parse_json_field(restaurant.get("image_urls", []))
    for img_url in image_urls:
        if isinstance(img_url, str) and img_url.startswith("http"):
            all_image_urls.append(img_url)
    
    # 4. Get images from menu_items
    menu_items = parse_json_field(restaurant.get("menu_items", []))
    for item in menu_items:
        if isinstance(item, dict):
            item_images = item.get("images", [])
            if isinstance(item_images, str):
                item_images = parse_json_field(item_images)
            for img in item_images:
                if isinstance(img, str) and img.startswith("http"):
                    all_image_urls.append(img)
    
    # 5. Get images from popular_dishes
    popular_dishes = parse_json_field(restaurant.get("popular_dishes", []))
    for dish in popular_dishes:
        if isinstance(dish, dict):
            dish_images = dish.get("images", [])
            if isinstance(dish_images, str):
                dish_images = parse_json_field(dish_images)
            for img in dish_images:
                if isinstance(img, str) and img.startswith("http"):
                    all_image_urls.append(img)
    
    # Remove duplicates
    seen = set()
    unique_urls = []
    for url in all_image_urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    if not unique_urls:
        print(f"  [WARNING] No image URLs found", flush=True)
        return {"uploaded": 0, "failed": 0}
    
    print(f"  [STATS] Found {len(unique_urls)} unique image URLs", flush=True)
    
    # Create temp directory for this restaurant
    temp_restaurant_dir = Path(temp_dir) / yelp_id
    temp_restaurant_dir.mkdir(parents=True, exist_ok=True)
    
    # Download images by extracting from page (like photo_miner_yelp.py)
    downloaded_files = []
    failed_downloads = 0
    
    print(f"  [DOWNLOAD] Extracting and downloading images from Yelp page...", flush=True)
    
    # Navigate to restaurant page FIRST to extract fresh image URLs
    page_image_urls = []
    if restaurant_url:
        try:
            print(f"    [NAV] Navigating to restaurant page...", flush=True)
            # Use networkidle to ensure page is fully loaded
            page.goto(restaurant_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)  # Wait longer for images to load
            print(f"    [OK] Page loaded", flush=True)
            
            # Try to find and click on photos section
            try:
                print(f"    [SEARCH] Looking for photos section...", flush=True)
                # Try multiple selectors for photo links/buttons
                photo_selectors = [
                    'a[href*="/photos"]',
                    'a[href*="/biz_photos"]',
                    'button[aria-label*="photo" i]',
                    '[data-testid*="photo"]',
                    '.photo-count',
                    'a:has-text("Photos")',
                    'a:has-text("photos")'
                ]
                
                for selector in photo_selectors:
                    try:
                        photo_link = page.query_selector(selector)
                        if photo_link:
                            print(f"    [PHOTO] Found photos link, clicking...", flush=True)
                            photo_link.click()
                            page.wait_for_timeout(3000)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"    [WARNING] Could not click photos (continuing): {e}", flush=True)
            
            # Scroll slowly to trigger lazy loading
            try:
                print(f"    [SCROLL] Scrolling to load images...", flush=True)
                page.evaluate("""
                    () => {
                        return new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 300;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if(totalHeight >= scrollHeight || totalHeight > 2000){
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        });
                    }
                """)
                page.wait_for_timeout(2000)
            except:
                pass
            
            # Extract actual image URLs from the page
            print(f"    [SEARCH] Extracting image URLs from page...", flush=True)
            try:
                page_image_urls = page.evaluate("""
                    () => {
                        const images = [];
                        const seen = new Set();
                        
                        // Find all image elements
                        const allImages = document.querySelectorAll('img');
                        
                        for (const img of allImages) {
                            let src = img.src || img.getAttribute('data-src') || 
                                     img.getAttribute('data-lazy-src') || 
                                     img.getAttribute('data-original') ||
                                     img.getAttribute('srcset');
                            if (!src) continue;
                            
                            // Handle srcset
                            if (src.includes(',')) {
                                src = src.split(',')[0].trim().split(' ')[0];
                            }
                            
                            // Only process Yelp CDN images
                            if (!src.includes('yelpcdn.com') || !src.includes('bphoto')) {
                                continue;
                            }
                            
                            // Get full resolution - try to get large version
                            if (src.includes('/348s.jpg') || src.includes('/348s')) {
                                src = src.replace(/\/348s\.jpg/g, '/l.jpg').replace(/\/348s/g, '/l');
                            } else if (src.includes('/258s.jpg') || src.includes('/258s')) {
                                src = src.replace(/\/258s\.jpg/g, '/l.jpg').replace(/\/258s/g, '/l');
                            } else if (src.includes('/o.jpg')) {
                                src = src.replace('/o.jpg', '/l.jpg');
                            } else if (src.includes('/s.jpg')) {
                                src = src.replace('/s.jpg', '/l.jpg');
                            }
                            
                            // Clean up the URL
                            if (src.includes('?')) {
                                src = src.split('?')[0];
                            }
                            if (src.includes('#')) {
                                src = src.split('#')[0];
                            }
                            
                            if (src && !seen.has(src)) {
                                seen.add(src);
                                images.push(src);
                            }
                        }
                        
                        return Array.from(seen).slice(0, 20);
                    }
                """)
                
                if page_image_urls and len(page_image_urls) > 0:
                    print(f"    [OK] Found {len(page_image_urls)} image URLs on page", flush=True)
                    # Use page URLs instead of stored URLs
                    unique_urls = page_image_urls[:10]
                else:
                    print(f"    [WARNING] No images found on page, using stored URLs...", flush=True)
            except Exception as eval_error:
                print(f"    [WARNING] Error extracting: {eval_error}, using stored URLs...", flush=True)
        except Exception as e:
            print(f"    [WARNING] Could not load restaurant page: {e}", flush=True)
            print(f"    [WARNING] Will try with stored URLs...", flush=True)
    
    # Download images
    for idx, img_url in enumerate(unique_urls[:10], 1):  # Limit to 10 images
        try:
            # Get file extension
            parsed = urlparse(img_url)
            ext = os.path.splitext(parsed.path)[1] or '.jpg'
            if '?' in ext:
                ext = ext.split('?')[0]
            
            # Create temp filename
            filename = f"{idx:03d}{ext}"
            temp_filepath = temp_restaurant_dir / filename
            
            # Skip if already exists
            if temp_filepath.exists():
                downloaded_files.append((img_url, str(temp_filepath)))
                print(f"    [SKIP] [{idx}/{min(len(unique_urls), 10)}] Already exists: {filename}", flush=True)
                continue
            
            # Download image using page context (has Yelp cookies)
            if download_image_with_page(page, img_url, str(temp_filepath)):
                downloaded_files.append((img_url, str(temp_filepath)))
                print(f"    [OK] [{idx}/{min(len(unique_urls), 10)}] Downloaded: {filename}", flush=True)
            else:
                failed_downloads += 1
                print(f"    [FAIL] [{idx}/{min(len(unique_urls), 10)}] Failed to download", flush=True)
        except Exception as e:
            failed_downloads += 1
            print(f"    [WARNING] [{idx}/{min(len(unique_urls), 10)}] Error: {e}", flush=True)
    
    if not downloaded_files:
        print(f"  [FAIL] No images downloaded", flush=True)
        return {"uploaded": 0, "failed": failed_downloads}
    
    # Select best header image BEFORE uploading (using local files for faster processing)
    header_image_url = None
    if downloaded_files and HEADER_SELECTOR_AVAILABLE:
        try:
            print(f"  [ART] Selecting best header image from {len(downloaded_files)} images...", flush=True)
            selector = HeaderSelector(use_aesthetic=True)
            local_paths = [local_path for _, local_path in downloaded_files]
            best_header_path = selector.pick_best_header(local_paths, verbose=True)
            
            if best_header_path:
                # Find the corresponding original URL
                for original_url, local_path in downloaded_files:
                    if local_path == best_header_path:
                        header_image_url = original_url
                        print(f"  [WINNER] Selected header: {os.path.basename(best_header_path)}", flush=True)
                        break
        except Exception as e:
            print(f"  [WARNING] Error selecting header image: {e}", flush=True)
            import traceback
            traceback.print_exc()
    elif downloaded_files and not HEADER_SELECTOR_AVAILABLE:
        # If HeaderSelector not available, just use the first image as header
        if downloaded_files:
            header_image_url = downloaded_files[0][0]
            print(f"  [INFO] HeaderSelector not available, using first image as header", flush=True)
    
    # Upload to Supabase Storage
    print(f"  [UPLOAD] Uploading {len(downloaded_files)} images to Supabase Storage...", flush=True)
    supabase_photos = []
    uploaded_count = 0
    failed_uploads = 0
    header_supabase_url = None  # Will store the Supabase URL of the header image
    
    for img_url, local_path in downloaded_files:
        try:
            # Upload to Supabase Storage
            public_url = upload_local_image_to_storage(
                local_path,
                bucket_name=bucket_name,
                folder="yelp",
                yelp_id=yelp_id
            )
            
            if public_url:
                supabase_photos.append(public_url)
                uploaded_count += 1
                
                # If this is the header image, save its Supabase URL
                if header_image_url and img_url == header_image_url:
                    header_supabase_url = public_url
                    print(f"    [HEADER] Header uploaded to: {public_url[:60]}...", flush=True)
                else:
                    print(f"    [OK] Uploaded to: {public_url[:60]}...", flush=True)
            else:
                failed_uploads += 1
                print(f"    [FAIL] Failed to upload", flush=True)
        except Exception as e:
            failed_uploads += 1
            print(f"    [WARNING] Error uploading: {e}", flush=True)
    
    # Clean up temp files
    try:
        import shutil
        shutil.rmtree(temp_restaurant_dir)
    except:
        pass
    
    # Update restaurant record with Supabase URLs
    if supabase_photos:
        # Map original URLs to Supabase URLs (for menu_items and popular_dishes)
        url_mapping = {}
        for idx, (original_url, _) in enumerate(downloaded_files):
            if idx < len(supabase_photos):
                url_mapping[original_url] = supabase_photos[idx]
        
        # Update menu_items with Supabase URLs
        updated_menu_items = None
        menu_items_data = parse_json_field(restaurant.get("menu_items", []))
        if menu_items_data:
            updated_menu_items = []
            for item in menu_items_data:
                if isinstance(item, dict):
                    updated_item = item.copy()
                    item_images = item.get("images", [])
                    if isinstance(item_images, str):
                        item_images = parse_json_field(item_images)
                    elif not isinstance(item_images, list):
                        item_images = []
                    
                    updated_item_images = []
                    for img in item_images:
                        if isinstance(img, str):
                            if img in url_mapping:
                                updated_item_images.append(url_mapping[img])
                            elif img.startswith("http"):
                                # Keep original if not mapped
                                updated_item_images.append(img)
                            else:
                                updated_item_images.append(img)
                    
                    updated_item["images"] = updated_item_images
                    updated_menu_items.append(updated_item)
                else:
                    updated_menu_items.append(item)
        
        # Update popular_dishes with Supabase URLs
        updated_popular_dishes = None
        popular_dishes_data = parse_json_field(restaurant.get("popular_dishes", []))
        if popular_dishes_data:
            updated_popular_dishes = []
            for dish in popular_dishes_data:
                if isinstance(dish, dict):
                    updated_dish = dish.copy()
                    dish_images = dish.get("images", [])
                    if isinstance(dish_images, str):
                        dish_images = parse_json_field(dish_images)
                    elif not isinstance(dish_images, list):
                        dish_images = []
                    
                    updated_dish_images = []
                    for img in dish_images:
                        if isinstance(img, str):
                            if img in url_mapping:
                                updated_dish_images.append(url_mapping[img])
                            elif img.startswith("http"):
                                # Keep original if not mapped
                                updated_dish_images.append(img)
                            else:
                                updated_dish_images.append(img)
                    
                    updated_dish["images"] = updated_dish_images
                    updated_popular_dishes.append(updated_dish)
                else:
                    updated_popular_dishes.append(dish)
        
        # Update restaurant record
        success = update_restaurant_with_photos_and_menu(
            yelp_id, supabase_photos, supabase_photos, 
            updated_menu_items, updated_popular_dishes,
            header_image_url=header_supabase_url
        )
        if success:
            print(f"  [OK] Updated restaurant record with {len(supabase_photos)} Supabase Storage URLs", flush=True)
            print(f"     Updated: photos, images, image_urls", flush=True)
            if header_supabase_url:
                print(f"     [HEADER] Updated: header_image_url", flush=True)
            if updated_menu_items:
                print(f"     Updated: menu_items ({len(updated_menu_items)} items)", flush=True)
            if updated_popular_dishes:
                print(f"     Updated: popular_dishes ({len(updated_popular_dishes)} dishes)", flush=True)
        else:
            print(f"  [WARNING] Failed to update restaurant record", flush=True)
    
    return {
        "uploaded": uploaded_count,
        "failed": failed_downloads + failed_uploads
    }


def download_and_upload_images(limit: Optional[int] = None, yelp_id: Optional[str] = None,
                               bucket_name: str = "restaurant-images", headless: bool = False,
                               allow_reprocess: bool = False):
    """Main function to download and upload images"""
    
    # Check Supabase connection
    print("[CHECK] Checking Supabase connection...", flush=True)
    supabase = get_supabase_client()
    if not supabase:
        print("[FAIL] Failed to connect to Supabase!", flush=True)
        return
    
    print("[OK] Connected to Supabase", flush=True)
    print()
    
    # Get restaurants
    print("[LOAD] Loading restaurants from Supabase...", flush=True)
    restaurants = get_restaurants_from_supabase(limit=limit, yelp_id=yelp_id, allow_reprocess=allow_reprocess)
    
    if not restaurants:
        print("[FAIL] No restaurants found", flush=True)
        return
    
    print(f"[OK] Found {len(restaurants)} restaurants to process", flush=True)
    print()
    
    # Setup browser
    brave_path = find_brave_path()
    if not brave_path:
        print("[WARNING] Brave browser not found. Using system default...", flush=True)
    
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    total_uploaded = 0
    total_failed = 0
    processed = 0
    
    with sync_playwright() as p:
        launch_options = {
            "headless": headless,
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        }
        
        if is_ci:
            launch_options["executable_path"] = "/usr/bin/chromium-browser"
            launch_options["args"].extend([
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--no-sandbox'
            ])
        elif brave_path:
            launch_options["executable_path"] = brave_path
        
        print("[START] Starting browser...", flush=True)
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Establish Yelp session
            print("[SESSION] Establishing Yelp session...", flush=True)
            page.goto("https://www.yelp.com", wait_until="load", timeout=30000)
            print("[OK] Session established", flush=True)
            print()
            
            # Process each restaurant
            for idx, restaurant in enumerate(restaurants, 1):
                print(f"[{idx}/{len(restaurants)}] ", end="", flush=True)
                result = process_restaurant_images(restaurant, page, bucket_name)
                total_uploaded += result["uploaded"]
                total_failed += result["failed"]
                processed += 1
                print()
        
        finally:
            browser.close()
    
    # Summary
    print()
    print("=" * 60, flush=True)
    print("SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"[OK] Processed: {processed} restaurants", flush=True)
    print(f"[IMAGES] Images uploaded: {total_uploaded}", flush=True)
    print(f"[FAIL] Failed: {total_failed}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download and upload Yelp images to Supabase")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of restaurants to process")
    parser.add_argument("--yelp-id", type=str, default=None,
                       help="Process specific restaurant by yelp_id")
    parser.add_argument("--bucket", default="restaurant-images",
                       help="Supabase Storage bucket name")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode")
    parser.add_argument("--reprocess", action="store_true",
                        help="Allow reprocessing restaurants that already have images")
    
    args = parser.parse_args()
    
    download_and_upload_images(
        limit=args.limit,
        yelp_id=args.yelp_id,
        bucket_name=args.bucket,
        headless=args.headless,
        allow_reprocess=args.reprocess
    )

