"""Supabase configuration and helper functions for Snowball Crawler"""
import os
from supabase import create_client, Client
from typing import List, Dict, Optional
import time
import requests
from io import BytesIO
from urllib.parse import urlparse
import hashlib
import unicodedata
import re

# Try to load from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required if using environment variables directly

# Supabase configuration - set these as environment variables.
# Re-read from environment each time to ensure we get the latest values.
def get_supabase_credentials():
    """Get Supabase credentials from environment variables."""
    url = os.getenv("SUPABASE_URL", "") or ""

    # Accept multiple env var names for the key to avoid CI misconfiguration.
    candidates = [
        os.getenv("SUPABASE_SERVICE_KEY", ""),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        os.getenv("SUPABASE_KEY", ""),
        os.getenv("SUPABASE_ANON_KEY", ""),
    ]

    # Strip whitespace/newlines (common with GitHub secrets)
    candidates = [c.strip() for c in candidates if c]
    key = ""
    for candidate in candidates:
        if candidate:
            key = candidate
            break

    return url.strip(), key

def get_supabase_client() -> Optional[Client]:
    """Create and return Supabase client"""
    SUPABASE_URL, SUPABASE_KEY = get_supabase_credentials()
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠ Warning: SUPABASE_URL and SUPABASE_KEY not set!")
        print("Set them as environment variables or update this file.")
        # Debug: Show what we got
        print(f"  SUPABASE_URL: {'SET' if SUPABASE_URL else 'NOT SET'}")
        print(f"  SUPABASE_KEY: {'SET' if SUPABASE_KEY else 'NOT SET'}")
        return None
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None

def add_urls_to_queue(urls: List[str], source_hashtag: str = None, source_url: str = None) -> int:
    """Add discovered URLs to the crawl queue (ignores duplicates)"""
    supabase = get_supabase_client()
    if not supabase:
        return 0
    
    added_count = 0
    skipped_count = 0
    
    for url in urls:
        try:
            # Check if URL already exists
            existing = supabase.table("crawl_queue").select("url").eq("url", url).execute()
            
            if existing.data:
                skipped_count += 1
                continue
            
            # Insert new URL
            result = supabase.table("crawl_queue").insert({
                "url": url,
                "source_hashtag": source_hashtag,
                "source_url": source_url,
                "status": "pending"
            }).execute()
            
            if result.data:
                added_count += 1
        except Exception as e:
            print(f"Error adding URL {url} to queue: {e}")
            continue
    
    print(f"✓ Added {added_count} new URLs to queue, skipped {skipped_count} duplicates")
    return added_count

def get_pending_urls(limit: int = 10) -> List[Dict]:
    """Get pending URLs from queue for processing"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        result = supabase.table("crawl_queue")\
            .select("*")\
            .eq("status", "pending")\
            .order("discovered_at", desc=False)\
            .limit(limit)\
            .execute()
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching pending URLs: {e}")
        return []

def mark_url_processing(url: str) -> bool:
    """Mark URL as being processed"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table("crawl_queue")\
            .update({"status": "processing"})\
            .eq("url", url)\
            .execute()
        return True
    except Exception as e:
        print(f"Error marking URL as processing: {e}")
        return False

def mark_url_completed(url: str) -> bool:
    """Mark URL as completed"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table("crawl_queue")\
            .update({
                "status": "completed",
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })\
            .eq("url", url)\
            .execute()
        return True
    except Exception as e:
        print(f"Error marking URL as completed: {e}")
        return False

def mark_url_failed(url: str, error_message: str = None) -> bool:
    """Mark URL as failed and increment retry count"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Get current retry count
        current = supabase.table("crawl_queue")\
            .select("retry_count")\
            .eq("url", url)\
            .execute()
        
        retry_count = current.data[0]["retry_count"] + 1 if current.data else 1
        max_retries = current.data[0].get("max_retries", 3) if current.data else 3
        
        # If exceeded max retries, mark as failed permanently
        status = "failed" if retry_count >= max_retries else "pending"
        
        supabase.table("crawl_queue")\
            .update({
                "status": status,
                "error_message": error_message,
                "retry_count": retry_count
            })\
            .eq("url", url)\
            .execute()
        return True
    except Exception as e:
        print(f"Error marking URL as failed: {e}")
        return False

def save_article_to_db(url: str, html_content: str = None, itinerary_data: Dict = None, 
                       extraction_error: str = None) -> bool:
    """Save scraped article and extracted data to database"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        data = {
            "url": url,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if html_content:
            data["html_content"] = html_content
            data["scraped_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if itinerary_data:
            data["itinerary_data"] = itinerary_data
            data["extracted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if extraction_error:
            data["extraction_error"] = extraction_error
        
        # Upsert (insert or update)
        supabase.table("lemon8_articles")\
            .upsert(data)\
            .execute()
        
        return True
    except Exception as e:
        print(f"Error saving article to database: {e}")
        return False

def get_failed_extractions(limit: int = None) -> List[Dict]:
    """Get articles that failed LLM extraction"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        query = supabase.table("lemon8_articles")\
            .select("*")\
            .not_.is_("extraction_error", "null")\
            .eq("extraction_error", "Failed to extract itinerary data")
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching failed extractions: {e}")
        return []

def is_seed_url_processed(source_url: str) -> bool:
    """Check if a seed URL has already been processed (has URLs in queue from this source)"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        result = supabase.table("crawl_queue")\
            .select("url", count="exact")\
            .eq("source_url", source_url)\
            .limit(1)\
            .execute()
        
        # If there are any URLs with this source_url, the seed has been processed
        count = result.count if hasattr(result, 'count') else (len(result.data) if result.data else 0)
        return count > 0
    except Exception as e:
        print(f"Error checking if seed URL is processed: {e}")
        return False  # If we can't check, assume not processed to be safe

def get_processed_seed_urls() -> set:
    """Get all source_urls that have been processed (more efficient for batch checking)"""
    supabase = get_supabase_client()
    if not supabase:
        return set()
    
    try:
        # Get all distinct source_urls from the queue
        result = supabase.table("crawl_queue")\
            .select("source_url")\
            .not_.is_("source_url", "null")\
            .execute()
        
        # Extract unique source_urls
        processed_urls = set()
        if result.data:
            for row in result.data:
                if row.get("source_url"):
                    processed_urls.add(row["source_url"])
        
        return processed_urls
    except Exception as e:
        print(f"Error getting processed seed URLs: {e}")
        return set()  # If we can't check, return empty set to be safe

def get_queue_stats() -> Dict:
    """Get statistics about the crawl queue"""
    supabase = get_supabase_client()
    if not supabase:
        return {}
    
    try:
        pending = supabase.table("crawl_queue")\
            .select("url", count="exact")\
            .eq("status", "pending")\
            .execute()
        
        processing = supabase.table("crawl_queue")\
            .select("url", count="exact")\
            .eq("status", "processing")\
            .execute()
        
        completed = supabase.table("crawl_queue")\
            .select("url", count="exact")\
            .eq("status", "completed")\
            .execute()
        
        failed = supabase.table("crawl_queue")\
            .select("url", count="exact")\
            .eq("status", "failed")\
            .execute()
        
        return {
            "pending": pending.count if hasattr(pending, 'count') else len(pending.data) if pending.data else 0,
            "processing": processing.count if hasattr(processing, 'count') else len(processing.data) if processing.data else 0,
            "completed": completed.count if hasattr(completed, 'count') else len(completed.data) if completed.data else 0,
            "failed": failed.count if hasattr(failed, 'count') else len(failed.data) if failed.data else 0,
        }
    except Exception as e:
        print(f"Error getting queue stats: {e}")
        return {}

# Yelp URL Queue Functions
def add_yelp_url_to_queue(yelp_id: str, yelp_url: str, place_name: str, city: str, 
                          lemon8_source: Dict, status: str = "pending") -> bool:
    """Add Yelp URL to crawl_queue_yelp table (ignores duplicates)"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Check if Yelp ID already exists
        existing = supabase.table("crawl_queue_yelp")\
            .select("yelp_id")\
            .eq("yelp_id", yelp_id)\
            .execute()
        
        if existing.data:
            return False  # Already exists
        
        # Insert new Yelp URL
        result = supabase.table("crawl_queue_yelp").insert({
            "yelp_id": yelp_id,
            "url": yelp_url,
            "place_name": place_name,
            "city": city,
            "lemon8_source": lemon8_source,
            "status": status,
            "discovered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        
        return bool(result.data)
    except Exception as e:
        print(f"Error adding Yelp URL to queue: {e}")
        return False

def get_processed_article_urls_for_yelp() -> set:
    """Get all article URLs that have been processed for Yelp URL discovery"""
    supabase = get_supabase_client()
    if not supabase:
        return set()
    
    try:
        # Get all distinct article URLs from crawl_queue_yelp
        result = supabase.table("crawl_queue_yelp")\
            .select("lemon8_source")\
            .not_.is_("lemon8_source", "null")\
            .execute()
        
        processed_urls = set()
        if result.data:
            for row in result.data:
                lemon8_source = row.get("lemon8_source", {})
                article_url = lemon8_source.get("article_url")
                if article_url:
                    processed_urls.add(article_url)
        
        return processed_urls
    except Exception as e:
        print(f"Error getting processed article URLs: {e}")
        return set()

def mark_article_yelp_scouted(article_url: str) -> bool:
    """Mark a lemon8_article as having been processed for Yelp URL discovery"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Update the article to mark it as Yelp-scouted
        # We'll use a JSONB field or add a boolean field
        # For now, we'll track it via the crawl_queue_yelp table
        # This function is for future use if we add a yelp_urls_scouted field
        return True
    except Exception as e:
        print(f"Error marking article as Yelp-scouted: {e}")
        return False


def save_yelp_restaurant_to_db(restaurant_data: Dict) -> bool:
    """Save scraped Yelp restaurant data to yelp_restaurants table"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Prepare data for Supabase (ensure proper types)
        db_data = {
            "yelp_id": restaurant_data.get("yelp_id"),
            "source": restaurant_data.get("source", "yelp"),
            "source_id": restaurant_data.get("source_id"),
            "source_url": restaurant_data.get("source_url"),
            "url": restaurant_data.get("url"),
            "name": restaurant_data.get("name"),
            "description": restaurant_data.get("description"),
            "address": restaurant_data.get("address"),
            "city": restaurant_data.get("city"),
            "state": restaurant_data.get("state"),
            "rating": restaurant_data.get("rating"),
            "total_reviews": restaurant_data.get("total_reviews"),
            "review_count": restaurant_data.get("review_count"),
            "price_range": restaurant_data.get("price_range"),
            "phone": restaurant_data.get("phone"),
            "website": restaurant_data.get("website"),
            "hours": restaurant_data.get("hours"),
            "categories": restaurant_data.get("categories", []),
            "cuisine": restaurant_data.get("cuisine"),
            "photos": restaurant_data.get("photos", []),
            "images": restaurant_data.get("images", []),
            "image_urls": restaurant_data.get("image_urls", []),
            "menu_items": restaurant_data.get("menu_items", []),
            "popular_dishes": restaurant_data.get("popular_dishes", []),
            "reviews": restaurant_data.get("reviews", []),
            "menu_link": restaurant_data.get("menu_link"),
            "amenities": restaurant_data.get("amenities", []),
            "location": restaurant_data.get("location"),
            "lemon8_source": restaurant_data.get("lemon8_source"),
            "scraped_at": restaurant_data.get("scraped_at")
        }
        
        # Upsert (insert or update)
        supabase.table("yelp_restaurants")\
            .upsert(db_data)\
            .execute()
        
        return True
    except Exception as e:
        print(f"Error saving Yelp restaurant to database: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def get_existing_scraped_yelp_ids() -> set:
    """Get all existing Yelp IDs from yelp_restaurants table"""
    supabase = get_supabase_client()
    if not supabase:
        return set()
    
    try:
        result = supabase.table("yelp_restaurants")\
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
        print(f"⚠️  Error loading existing scraped data: {e}", flush=True)
        return set()


def get_all_yelp_urls_from_queue(limit: Optional[int] = None) -> List[Dict]:
    """Get all Yelp URLs from crawl_queue_yelp table (all statuses)"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        query = supabase.table("crawl_queue_yelp")\
            .select("*")\
            .order("discovered_at", desc=False)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting all Yelp URLs from queue: {e}", flush=True)
        return []


def get_pending_yelp_urls(limit: Optional[int] = None) -> List[Dict]:
    """Get pending Yelp URLs from crawl_queue_yelp table"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        query = supabase.table("crawl_queue_yelp")\
            .select("*")\
            .eq("status", "pending")\
            .order("discovered_at", desc=False)
        
        if limit:
            query = query.limit(limit)
        
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error getting pending Yelp URLs: {e}", flush=True)
        return []


def mark_yelp_url_processing(yelp_id: str) -> bool:
    """Mark Yelp URL as processing in crawl_queue_yelp table"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table("crawl_queue_yelp")\
            .update({
                "status": "processing",
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })\
            .eq("yelp_id", yelp_id)\
            .execute()
        return True
    except Exception as e:
        print(f"Error marking Yelp URL as processing: {e}", flush=True)
        return False


def mark_yelp_url_completed(yelp_id: str) -> bool:
    """Mark Yelp URL as completed in crawl_queue_yelp table"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        supabase.table("crawl_queue_yelp")\
            .update({
                "status": "completed",
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })\
            .eq("yelp_id", yelp_id)\
            .execute()
        return True
    except Exception as e:
        print(f"Error marking Yelp URL as completed: {e}", flush=True)
        return False


def mark_yelp_url_failed(yelp_id: str, error_message: str = None) -> bool:
    """Mark Yelp URL as failed in crawl_queue_yelp table"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        update_data = {
            "status": "failed",
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if error_message:
            update_data["error_message"] = error_message
        
        supabase.table("crawl_queue_yelp")\
            .update(update_data)\
            .eq("yelp_id", yelp_id)\
            .execute()
        return True
    except Exception as e:
        print(f"Error marking Yelp URL as failed: {e}", flush=True)
        return False


def get_yelp_queue_stats() -> Dict:
    """Get statistics for crawl_queue_yelp table"""
    supabase = get_supabase_client()
    if not supabase:
        return {}
    
    try:
        pending = supabase.table("crawl_queue_yelp")\
            .select("yelp_id", count="exact")\
            .eq("status", "pending")\
            .execute()
        
        processing = supabase.table("crawl_queue_yelp")\
            .select("yelp_id", count="exact")\
            .eq("status", "processing")\
            .execute()
        
        completed = supabase.table("crawl_queue_yelp")\
            .select("yelp_id", count="exact")\
            .eq("status", "completed")\
            .execute()
        
        failed = supabase.table("crawl_queue_yelp")\
            .select("yelp_id", count="exact")\
            .eq("status", "failed")\
            .execute()
        
        return {
            "pending": pending.count if hasattr(pending, 'count') else len(pending.data) if pending.data else 0,
            "processing": processing.count if hasattr(processing, 'count') else len(processing.data) if processing.data else 0,
            "completed": completed.count if hasattr(completed, 'count') else len(completed.data) if completed.data else 0,
            "failed": failed.count if hasattr(failed, 'count') else len(failed.data) if failed.data else 0,
        }
    except Exception as e:
        print(f"Error getting Yelp queue stats: {e}", flush=True)
        return {}


def sanitize_storage_key(key: str) -> str:
    """
    Sanitize a string to be used as a Supabase Storage key.
    Supabase Storage keys must be URL-safe and cannot contain special Unicode characters.
    """
    if not key:
        return key
    
    # Normalize Unicode characters (NFD = decomposed form, then remove combining marks)
    # This converts characters like "ō" to "o"
    normalized = unicodedata.normalize('NFD', key)
    # Remove combining characters (accents, diacritics)
    ascii_key = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    
    # Replace spaces with hyphens
    ascii_key = ascii_key.replace(' ', '-')
    
    # Remove or replace invalid characters (keep only alphanumeric, hyphens, underscores, dots, forward slashes)
    # Supabase Storage allows: a-z, A-Z, 0-9, -, _, ., /
    ascii_key = re.sub(r'[^a-zA-Z0-9\-_./]', '', ascii_key)
    
    # Remove consecutive hyphens/underscores
    ascii_key = re.sub(r'[-_]{2,}', '-', ascii_key)
    
    # Remove leading/trailing hyphens and underscores
    ascii_key = ascii_key.strip('-_')
    
    return ascii_key


def upload_image_to_storage(image_url: str, bucket_name: str = "restaurant-images", 
                           folder: str = "yelp", yelp_id: str = None) -> Optional[str]:
    """
    Download an image from URL and upload to Supabase Storage.
    Returns the public URL of the uploaded image, or None if failed.
    """
    supabase = get_supabase_client()
    if not supabase:
        return None
    
    try:
        # Download image
        response = requests.get(image_url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.yelp.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
        })
        response.raise_for_status()
        
        # Generate filename from URL
        parsed_url = urlparse(image_url)
        filename = parsed_url.path.split('/')[-1]
        if not filename or '.' not in filename:
            # Generate filename from hash if no extension
            filename = hashlib.md5(image_url.encode()).hexdigest() + '.jpg'
        
        # Clean filename (remove query params if any)
        if '?' in filename:
            filename = filename.split('?')[0]
        
        # Sanitize filename and yelp_id for storage keys
        filename = sanitize_storage_key(filename)
        sanitized_yelp_id = sanitize_storage_key(yelp_id) if yelp_id else None
        
        # Create storage path: folder/yelp_id/filename or folder/filename
        if sanitized_yelp_id:
            storage_path = f"{folder}/{sanitized_yelp_id}/{filename}"
        else:
            storage_path = f"{folder}/{filename}"
        
        # Upload to Supabase Storage
        file_data = BytesIO(response.content)
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        # Check if file already exists (optional - can skip if you want to overwrite)
        try:
            existing = supabase.storage.from_(bucket_name).list(storage_path)
            if existing:
                # File exists, get public URL
                public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
                return public_url
        except:
            pass  # File doesn't exist, continue with upload
        
        result = supabase.storage.from_(bucket_name).upload(
            storage_path,
            file_data.read(),
            file_options={"content-type": content_type, "upsert": "true"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
        return public_url
        
    except Exception as e:
        print(f"⚠️  Error uploading image {image_url}: {e}", flush=True)
        return None


def upload_local_image_to_storage(local_path: str, bucket_name: str = "restaurant-images",
                                 folder: str = "yelp", yelp_id: str = None) -> Optional[str]:
    """
    Upload a local image file to Supabase Storage.
    Returns the public URL of the uploaded image, or None if failed.
    """
    supabase = get_supabase_client()
    if not supabase:
        return None
    
    if not os.path.exists(local_path):
        print(f"⚠️  Local file not found: {local_path}", flush=True)
        return None
    
    try:
        # Get filename from local path
        filename = os.path.basename(local_path)
        
        # Sanitize filename and yelp_id for storage keys
        filename = sanitize_storage_key(filename)
        sanitized_yelp_id = sanitize_storage_key(yelp_id) if yelp_id else None
        
        # Create storage path: folder/yelp_id/filename or folder/filename
        if sanitized_yelp_id:
            storage_path = f"{folder}/{sanitized_yelp_id}/{filename}"
        else:
            storage_path = f"{folder}/{filename}"
        
        # Read file
        with open(local_path, 'rb') as f:
            file_data = f.read()
        
        # Determine content type
        ext = os.path.splitext(filename)[1].lower()
        content_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        content_type = content_type_map.get(ext, 'image/webp')  # Default to webp for optimized images
        
        # Upload to Supabase Storage
        result = supabase.storage.from_(bucket_name).upload(
            storage_path,
            file_data,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(storage_path)
        return public_url
        
    except Exception as e:
        print(f"⚠️  Error uploading local image {local_path}: {e}", flush=True)
        return None


def upload_images_batch(image_urls: List[str], bucket_name: str = "restaurant-images",
                        folder: str = "yelp", yelp_id: str = None) -> List[str]:
    """
    Upload multiple images from URLs and return list of public URLs.
    """
    uploaded_urls = []
    for image_url in image_urls:
        if not image_url:
            continue
        public_url = upload_image_to_storage(image_url, bucket_name, folder, yelp_id)
        if public_url:
            uploaded_urls.append(public_url)
    return uploaded_urls