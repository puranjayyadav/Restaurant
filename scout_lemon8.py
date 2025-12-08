"""Scout: Discovers Lemon8 article URLs and adds them to Supabase queue"""
import os
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from urllib.parse import urljoin
from supabase_config import add_urls_to_queue, get_queue_stats

# Default seed URLs - can be passed as arguments
DEFAULT_SEED_URLS = [
    "https://www.lemon8-app.com/experience/new-york-eat?region=us",
    # Add more seed URLs here (hashtags, influencer pages, etc.)
]

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

def auto_scroll(driver, scroll_pause_time=0.5, max_scrolls=50):
    """Smoothly scroll down the page to load dynamic content"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollBy(0, 500);")
        scroll_count += 1
        time.sleep(scroll_pause_time)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
        
        last_height = new_height
        
        if scroll_count % 10 == 0:
            print(f"  Scrolled {scroll_count} times...")
    
    return scroll_count

def discover_article_urls(driver, seed_url, max_scrolls=50):
    """Discover article URLs from a seed URL"""
    print(f"\n🔍 Discovering URLs from: {seed_url}")
    
    try:
        driver.get(seed_url)
        time.sleep(3)  # Wait for initial load
        
        print("  Auto-scrolling to load content...")
        auto_scroll(driver, scroll_pause_time=0.5, max_scrolls=max_scrolls)
        
        # Extract article links
        article_links = []
        base_url = "https://www.lemon8-app.com"
        seen_links = set()
        
        article_cards = driver.find_elements(By.CSS_SELECTOR, "a.article-recommend-card")
        print(f"  Found {len(article_cards)} article cards")
        
        for card in article_cards:
            try:
                href = card.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        full_url = urljoin(base_url, href)
                    elif href.startswith("http"):
                        full_url = href
                    else:
                        full_url = urljoin(base_url, "/" + href)
                    
                    if full_url not in seen_links:
                        seen_links.add(full_url)
                        article_links.append(full_url)
            except Exception as e:
                continue
        
        print(f"  ✓ Discovered {len(article_links)} unique article URLs")
        return article_links
        
    except Exception as e:
        print(f"  ✗ Error discovering URLs: {e}")
        return []

def main():
    """Main scout function"""
    print("=" * 60)
    print("🌱 LEMON8 SCOUT - URL Discovery")
    print("=" * 60)
    
    # Get seed URLs from command line or use defaults
    seed_urls = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_SEED_URLS
    
    if not seed_urls:
        print("No seed URLs provided!")
        print("Usage: python scout_lemon8.py <url1> <url2> ...")
        sys.exit(1)
    
    # Check Supabase connection
    stats = get_queue_stats()
    if stats:
        print(f"\n📊 Current Queue Stats:")
        print(f"  Pending: {stats.get('pending', 0)}")
        print(f"  Processing: {stats.get('processing', 0)}")
        print(f"  Completed: {stats.get('completed', 0)}")
        print(f"  Failed: {stats.get('failed', 0)}")
    else:
        print("⚠ Warning: Could not connect to Supabase. Check your credentials.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Find Brave (optional - will use system Chrome in CI)
    brave_path = find_brave_path()
    if brave_path:
        print(f"\n✓ Found Brave at: {brave_path}")
    else:
        print("\n⚠ Brave not found, using system Chrome/Chromium")
    
    # Setup driver
    driver = setup_driver(brave_path)
    driver.set_page_load_timeout(30)
    
    total_discovered = 0
    
    try:
        for seed_url in seed_urls:
            print(f"\n{'='*60}")
            print(f"Processing seed URL: {seed_url}")
            
            # Discover URLs from this seed
            urls = discover_article_urls(driver, seed_url, max_scrolls=50)
            
            if urls:
                # Extract hashtag from URL if possible
                source_hashtag = None
                if "hashtag" in seed_url or "experience" in seed_url:
                    source_hashtag = seed_url.split("/")[-1].split("?")[0]
                
                # Add to queue
                added = add_urls_to_queue(
                    urls=urls,
                    source_hashtag=source_hashtag,
                    source_url=seed_url
                )
                total_discovered += added
                
                # Rate limiting - be respectful
                time.sleep(2)
            else:
                print(f"  ⚠ No URLs discovered from {seed_url}")
        
        print(f"\n{'='*60}")
        print(f"✓ Scout completed!")
        print(f"  Total new URLs added to queue: {total_discovered}")
        
        # Show updated stats
        stats = get_queue_stats()
        if stats:
            print(f"\n📊 Updated Queue Stats:")
            print(f"  Pending: {stats.get('pending', 0)}")
            print(f"  Processing: {stats.get('processing', 0)}")
            print(f"  Completed: {stats.get('completed', 0)}")
            print(f"  Failed: {stats.get('failed', 0)}")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Scout interrupted by user.")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n✓ Browser closed.")

if __name__ == "__main__":
    main()
