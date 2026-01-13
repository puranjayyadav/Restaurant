"""Reprocess articles that failed LLM extraction"""
import os
import sys
import time
from supabase_config import get_supabase_client, get_failed_extractions
from extract_itineraries_from_articles import extract_itinerary_data

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def reprocess_article(article):
    """Reprocess a single article with LLM extraction"""
    url = article.get("url", "")
    html_content = article.get("html_content", "")
    
    if not html_content:
        print(f"  ⚠ No HTML content for {url}, skipping...")
        return False
    
    print(f"  Reprocessing: {url}")
    print(f"  HTML content length: {len(html_content)} characters")
    
    # Extract itinerary data using LLM
    def log_func(msg):
        print(f"    {msg}")
    
    itinerary_data = extract_itinerary_data(html_content, log_func=log_func)
    
    # Update database
    supabase = get_supabase_client()
    if not supabase:
        print("  ⚠ Could not connect to Supabase for update")
        return False
    
    try:
        update_data = {
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if itinerary_data:
            update_data["itinerary_data"] = itinerary_data
            update_data["extracted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            update_data["extraction_error"] = None  # Clear the error
            print(f"  ✓ Successfully extracted {len(itinerary_data.get('stops', []))} stops")
        else:
            update_data["extraction_error"] = "Failed to extract itinerary data (retry)"
            update_data["extracted_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  ✗ Still failed to extract itinerary data")
        
        supabase.table("lemon8_articles")\
            .update(update_data)\
            .eq("url", url)\
            .execute()
        
        return itinerary_data is not None
    except Exception as e:
        print(f"  ✗ Error updating database: {e}")
        return False

def main():
    """Main reprocessing function"""
    print("=" * 60)
    print("🔄 REPROCESS FAILED EXTRACTIONS")
    print("=" * 60)
    
    # Get limit from command line or use None (process all)
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"⚠ Invalid limit '{sys.argv[1]}', processing all failed articles")
    
    # Get failed articles
    print("\n📋 Fetching failed articles...")
    failed_articles = get_failed_extractions(limit=limit)
    
    if not failed_articles:
        print("✓ No failed articles found!")
        return
    
    print(f"✓ Found {len(failed_articles)} failed article(s) to reprocess")
    
    # Process each article
    success_count = 0
    still_failed_count = 0
    
    for idx, article in enumerate(failed_articles, 1):
        print(f"\n[{idx}/{len(failed_articles)}] Processing article...")
        
        success = reprocess_article(article)
        
        if success:
            success_count += 1
        else:
            still_failed_count += 1
        
        # Rate limiting - be respectful to LLM API
        if idx < len(failed_articles):
            print("  Waiting 5 seconds before next article...")
            time.sleep(5)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 REPROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"  Total processed: {len(failed_articles)}")
    print(f"  ✓ Successfully extracted: {success_count}")
    print(f"  ✗ Still failed: {still_failed_count}")
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
