"""Supabase configuration and helper functions for Snowball Crawler"""
import os
from supabase import create_client, Client
from typing import List, Dict, Optional
import time

# Try to load from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required if using environment variables directly

# Supabase configuration - set these as environment variables
# Re-read from environment each time to ensure we get the latest values
def get_supabase_credentials():
    """Get Supabase credentials from environment variables"""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    # Strip whitespace and newlines (common issue with GitHub Secrets)
    url = url.strip() if url else ""
    key = key.strip() if key else ""
    return url, key

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
