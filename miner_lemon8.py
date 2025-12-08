"""Miner: Processes URLs from queue, scrapes content, extracts with LLM, saves to Supabase"""
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from supabase_config import (
    get_pending_urls, mark_url_processing, mark_url_completed, 
    mark_url_failed, save_article_to_db, get_queue_stats
)
# Import LLM extraction functions
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extract_itineraries_from_articles import extract_itinerary_data

def find_brave_path():
    """Find Brave browser executable"""
    brave_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    
    for path in brave_paths:
        if os.path.exists(path):
            return path
    return None

def setup_driver(brave_path=None):
    """Setup Selenium WebDriver with Brave (or Chrome in CI)"""
    options = Options()
    
    # Use Brave if available, otherwise use system Chrome (for GitHub Actions)
    if brave_path and os.path.exists(brave_path):
        options.binary_location = brave_path
    else:
        # For GitHub Actions, use system Chrome
        options.binary_location = "/usr/bin/chromium-browser"
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--headless')  # Run headless for automation
    options.add_argument('--no-sandbox')  # Required for GitHub Actions
    options.add_argument('--disable-dev-shm-usage')  # Required for GitHub Actions
    
    return webdriver.Chrome(options=options)

def scrape_article_content(driver, url):
    """Scrape article content from a single page"""
    try:
        driver.get(url)
        time.sleep(2)  # Wait for page to load
        
        # Wait for article content section
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "article-content"))
            )
        except TimeoutException:
            time.sleep(3)  # Wait a bit more for dynamic content
        
        # Get the HTML content
        try:
            article_section = driver.find_element(By.ID, "article-content")
            article_html = article_section.get_attribute('outerHTML')
            
            if article_html:
                return article_html
            else:
                return None
        except NoSuchElementException:
            return None
            
    except Exception as e:
        print(f"  ✗ Error scraping: {e}")
        return None

def process_url(driver, url_data, log_func=None):
    """Process a single URL: scrape, extract, save"""
    if log_func is None:
        log_func = print
    
    url = url_data["url"]
    log_func(f"\n📄 Processing: {url}")
    
    # Mark as processing
    mark_url_processing(url)
    
    try:
        # Step 1: Scrape HTML content
        log_func("  Step 1: Scraping HTML content...")
        html_content = scrape_article_content(driver, url)
        
        if not html_content:
            error_msg = "Failed to scrape HTML content"
            log_func(f"  ✗ {error_msg}")
            mark_url_failed(url, error_msg)
            save_article_to_db(url, extraction_error=error_msg)
            return False
        
        log_func(f"  ✓ Scraped {len(html_content)} characters")
        save_article_to_db(url, html_content=html_content)
        
        # Step 2: Extract itinerary data with LLM
        log_func("  Step 2: Extracting itinerary data with LLM...")
        
        def llm_log(msg):
            log_func(f"    {msg}")
        
        itinerary_data = extract_itinerary_data(html_content, log_func=llm_log)
        
        if itinerary_data:
            log_func(f"  ✓ Extracted {len(itinerary_data.get('stops', []))} stops")
            save_article_to_db(url, html_content=html_content, itinerary_data=itinerary_data)
        else:
            error_msg = "Failed to extract itinerary data"
            log_func(f"  ⚠ {error_msg}")
            save_article_to_db(url, html_content=html_content, extraction_error=error_msg)
        
        # Mark as completed
        mark_url_completed(url)
        log_func(f"  ✓ Completed successfully")
        return True
        
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        log_func(f"  ✗ {error_msg}")
        mark_url_failed(url, error_msg)
        save_article_to_db(url, extraction_error=error_msg)
        return False

def main():
    """Main miner function"""
    print("=" * 60)
    print("⛏️  LEMON8 MINER - Queue Processor")
    print("=" * 60)
    
    # Get batch size from command line or use default
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10
    
    # Show queue stats
    stats = get_queue_stats()
    if stats:
        print(f"\n📊 Queue Stats:")
        print(f"  Pending: {stats.get('pending', 0)}")
        print(f"  Processing: {stats.get('processing', 0)}")
        print(f"  Completed: {stats.get('completed', 0)}")
        print(f"  Failed: {stats.get('failed', 0)}")
    else:
        print("⚠ Warning: Could not connect to Supabase. Check your credentials.")
        sys.exit(1)
    
    if stats.get('pending', 0) == 0:
        print("\n✓ No pending URLs to process. Queue is empty!")
        return
    
    # Find Brave (optional - will use system Chrome in CI)
    brave_path = find_brave_path()
    if brave_path:
        print(f"\n✓ Found Brave at: {brave_path}")
    else:
        print("\n⚠ Brave not found, using system Chrome/Chromium")
    
    print(f"📦 Processing batch of {batch_size} URLs...")
    
    # Setup driver
    driver = setup_driver(brave_path)
    driver.set_page_load_timeout(30)
    
    processed_count = 0
    success_count = 0
    error_count = 0
    
    try:
        while True:
            # Get pending URLs
            pending_urls = get_pending_urls(limit=batch_size)
            
            if not pending_urls:
                print("\n✓ No more pending URLs to process!")
                break
            
            print(f"\n{'='*60}")
            print(f"Processing {len(pending_urls)} URLs...")
            
            for url_data in pending_urls:
                success = process_url(driver, url_data)
                processed_count += 1
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                
                # Rate limiting - be respectful
                time.sleep(3)  # 3 second delay between URLs
            
            # Show progress
            print(f"\n📊 Progress:")
            print(f"  Processed: {processed_count}")
            print(f"  Successful: {success_count}")
            print(f"  Errors: {error_count}")
            
            # Check if we should continue
            remaining = get_queue_stats().get('pending', 0)
            if remaining == 0:
                break
            
            print(f"\n  {remaining} URLs remaining in queue...")
            time.sleep(2)  # Brief pause before next batch
        
        print(f"\n{'='*60}")
        print(f"✓ Mining completed!")
        print(f"  Total processed: {processed_count}")
        print(f"  Successful: {success_count}")
        print(f"  Errors: {error_count}")
        
        # Show final stats
        stats = get_queue_stats()
        if stats:
            print(f"\n📊 Final Queue Stats:")
            print(f"  Pending: {stats.get('pending', 0)}")
            print(f"  Processing: {stats.get('processing', 0)}")
            print(f"  Completed: {stats.get('completed', 0)}")
            print(f"  Failed: {stats.get('failed', 0)}")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Mining interrupted by user.")
        print("Progress has been saved to database.")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n✓ Browser closed.")

if __name__ == "__main__":
    main()
