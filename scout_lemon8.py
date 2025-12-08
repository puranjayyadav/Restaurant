"""Scout: Discovers Lemon8 article URLs and adds them to Supabase queue"""
import os
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from urllib.parse import urljoin, quote

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required if using environment variables directly

from supabase_config import add_urls_to_queue, get_queue_stats

def get_nyc_seed_urls():
    """
    Generate high-value NYC seed URLs using Neighborhood + Intent strategy.
    This creates targeted search URLs that Lemon8 users actually use.
    """
    # 1. Primary Locations (The "Hot" spots)
    neighborhoods = [
        # Manhattan (Downtown)
        "SoHo", "West Village", "East Village", "Lower East Side", "Chinatown",
        "Tribeca", "Nolita", "Greenwich Village", "NoHo", "Financial District",
        # Manhattan (Mid/Uptown)
        "Chelsea", "Flatiron", "Nomad", "Hell's Kitchen", "Upper West Side",
        "Upper East Side", "Harlem", "Washington Heights",
        # Brooklyn (The "Cool" Belt)
        "Williamsburg", "Greenpoint", "Bushwick", "DUMBO", "Brooklyn Heights",
        "Cobble Hill", "Carroll Gardens", "Fort Greene", "Bed-Stuy", "Park Slope",
        # Queens (Foodie Hubs)
        "Astoria", "Long Island City", "Jackson Heights", "Flushing", "Ridgewood",
    ]
    
    # 2. High-Intent Keywords
    intents = [
        "food guide", "best restaurants", "hidden gems", "itinerary",
        "things to do", "date night", "coffee shops", "thrift stores",
        "photo spots", "weekend guide", "cheap eats", "solo date",
        "speakeasy", "rooftop bars", "sample sales", "brunch spots",
        "dessert places", "pizza", "bagels", "sushi", "pasta", "tacos",
        "aesthetic places", "instagrammable", "non touristy",
        "girls night", "luxury", "budget friendly"
    ]
    
    # 3. "Mega" Keywords (Broad searches that return high volume)
    mega_keywords = [
        "NYC itinerary 3 days",
        "NYC aesthetic places",
        "New York non touristy things to do",
        "NYC food bucket list",
        "NYC weekend recap",
        "NYC rainy day activities",
        "Best photo spots NYC",
        "NYC hidden gems",
        "NYC date night ideas",
        "NYC solo date ideas"
    ]
    
    # Generate the URLs
    base_url = "https://www.lemon8-app.com/discover/"
    all_urls = []
    
    # A. Neighborhood + Intent Combinations (e.g., "SoHo NYC hidden gems")
    for hood in neighborhoods:
        for intent in intents:
            query = f"{hood} NYC {intent}"  # Adding "NYC" helps disambiguate
            encoded = quote(query)
            all_urls.append(f"{base_url}{encoded}?region=us")
    
    # B. Mega Keywords (standalone high-volume searches)
    for keyword in mega_keywords:
        encoded = quote(keyword)
        all_urls.append(f"{base_url}{encoded}?region=us")
    
    # C. Keep some experience/hashtag URLs for variety
    experience_urls = [
        "https://www.lemon8-app.com/experience/new-york-eat?region=us",
        "https://www.lemon8-app.com/experience/new-york-travel?region=us",
        "https://www.lemon8-app.com/experience/new-york-lifestyle?region=us",
    ]
    all_urls.extend(experience_urls)
    
    return all_urls

# Default seed URLs - generated dynamically using NYC strategy
DEFAULT_SEED_URLS = get_nyc_seed_urls()

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
    
    # Check if running in CI (non-interactive environment)
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    
    # Debug: Show environment variable status (only first few chars for security)
    if is_ci:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        print(f"\n🔍 Environment Check (CI mode):")
        print(f"  SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'} ({supabase_url[:30] + '...' if supabase_url else 'N/A'})")
        print(f"  SUPABASE_KEY: {'SET' if supabase_key else 'NOT SET'} ({supabase_key[:20] + '...' if supabase_key else 'N/A'})")
    
    # Get seed URLs from command line or use defaults
    if len(sys.argv) > 1:
        # Check if first arg is a number (limit) or a URL
        try:
            limit = int(sys.argv[1])
            # First arg is a limit number
            seed_urls = DEFAULT_SEED_URLS[:limit] if limit > 0 else DEFAULT_SEED_URLS
            print(f"\n📋 Using first {len(seed_urls)} of {len(DEFAULT_SEED_URLS)} generated NYC seed URLs")
        except ValueError:
            # First arg is a URL (or not a number)
            seed_urls = sys.argv[1:]
            print(f"\n📋 Using {len(seed_urls)} manually provided seed URL(s)")
    else:
        # Use all auto-generated NYC seed URLs
        seed_urls = DEFAULT_SEED_URLS
        print(f"\n📋 Generated {len(seed_urls)} NYC seed URLs using Neighborhood + Intent strategy")
        print(f"  Example URLs:")
        for i, url in enumerate(seed_urls[:3], 1):
            print(f"    {i}. {url}")
        if len(seed_urls) > 3:
            print(f"    ... and {len(seed_urls) - 3} more")
        print(f"\n  💡 Tip: Limit URLs by running: python scout_lemon8.py 50")
    
    if not seed_urls:
        print("No seed URLs available!")
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
        # Always exit in CI - never prompt for input
        if is_ci:
            print("⚠ Running in CI environment - exiting due to Supabase connection failure")
            print("⚠ Make sure SUPABASE_URL and SUPABASE_KEY are set as GitHub Secrets")
            print("⚠ Also check that there are no extra spaces or newlines in the secret values")
            sys.exit(1)
        else:
            # Only prompt in local (non-CI) environment
            try:
                response = input("Continue anyway? (y/n): ")
                if response.lower() != 'y':
                    sys.exit(1)
            except (EOFError, KeyboardInterrupt):
                # Handle case where stdin is not available
                print("⚠ Cannot read input - exiting")
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
