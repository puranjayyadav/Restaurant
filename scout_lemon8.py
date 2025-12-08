"""Scout: Discovers Lemon8 article URLs and adds them to Supabase queue"""
import os
import sys

# Force unbuffered output for CI environments
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        # Python < 3.7 doesn't have reconfigure, use flush instead
        pass

# Immediate output to confirm script started
print("=" * 60, flush=True)
print("SCRIPT STARTED - scout_lemon8.py", flush=True)
print("=" * 60, flush=True)
sys.stdout.flush()

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

print("Importing supabase_config...", flush=True)
sys.stdout.flush()

from supabase_config import add_urls_to_queue, get_queue_stats

print("All imports successful", flush=True)
sys.stdout.flush()

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
    print("Setting up Chrome driver options...", flush=True)
    sys.stdout.flush()
    
    options = Options()
    
    # Use Brave if available, otherwise use system Chrome (for GitHub Actions)
    if brave_path and os.path.exists(brave_path):
        options.binary_location = brave_path
        print(f"Using Brave browser at: {brave_path}", flush=True)
    else:
        # For GitHub Actions, use system Chrome
        options.binary_location = "/usr/bin/chromium-browser"
        print("Using system Chromium browser", flush=True)
    
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--headless')  # Run headless for automation
    options.add_argument('--no-sandbox')  # Required for GitHub Actions
    options.add_argument('--disable-dev-shm-usage')  # Required for GitHub Actions
    
    print("Creating WebDriver instance...", flush=True)
    sys.stdout.flush()
    
    try:
        driver = webdriver.Chrome(options=options)
        print("✓ WebDriver created successfully", flush=True)
        sys.stdout.flush()
        return driver
    except Exception as e:
        print(f"✗ Failed to create WebDriver: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        raise

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
            print(f"  Scrolled {scroll_count} times...", flush=True)
            sys.stdout.flush()
    
    return scroll_count

def discover_article_urls(driver, seed_url, max_scrolls=50):
    """Discover article URLs from a seed URL"""
    print(f"\n🔍 Discovering URLs from: {seed_url}", flush=True)
    sys.stdout.flush()
    
    try:
        print(f"  Loading page...", flush=True)
        sys.stdout.flush()
        driver.get(seed_url)
        print(f"  Page loaded, waiting 3 seconds...", flush=True)
        sys.stdout.flush()
        time.sleep(3)  # Wait for initial load
        
        print("  Auto-scrolling to load content...", flush=True)
        sys.stdout.flush()
        auto_scroll(driver, scroll_pause_time=0.5, max_scrolls=max_scrolls)
        
        # Extract article links
        article_links = []
        base_url = "https://www.lemon8-app.com"
        seen_links = set()
        
        print(f"  Extracting article links...", flush=True)
        sys.stdout.flush()
        article_cards = driver.find_elements(By.CSS_SELECTOR, "a.article-recommend-card")
        print(f"  Found {len(article_cards)} article cards", flush=True)
        sys.stdout.flush()
        
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
        
        print(f"  ✓ Discovered {len(article_links)} unique article URLs", flush=True)
        sys.stdout.flush()
        return article_links
        
    except Exception as e:
        print(f"  ✗ Error discovering URLs: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return []

def main():
    """Main scout function"""
    print("=" * 60, flush=True)
    print("🌱 LEMON8 SCOUT - URL Discovery", flush=True)
    print("=" * 60, flush=True)
    sys.stdout.flush()
    
    # Check if running in CI (non-interactive environment)
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    print(f"Running in CI environment: {is_ci}", flush=True)
    sys.stdout.flush()
    
    # Debug: Show environment variable status (only first few chars for security)
    if is_ci:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        print(f"\n🔍 Environment Check (CI mode):", flush=True)
        print(f"  SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'} ({supabase_url[:30] + '...' if supabase_url else 'N/A'})", flush=True)
        print(f"  SUPABASE_KEY: {'SET' if supabase_key else 'NOT SET'} ({supabase_key[:20] + '...' if supabase_key else 'N/A'})", flush=True)
        sys.stdout.flush()
    
    # Get seed URLs from command line or use defaults
    print("\n📋 Processing seed URLs...", flush=True)
    sys.stdout.flush()
    if len(sys.argv) > 1:
        # Check if first arg is a number (limit) or a URL
        try:
            limit = int(sys.argv[1])
            # First arg is a limit number
            seed_urls = DEFAULT_SEED_URLS[:limit] if limit > 0 else DEFAULT_SEED_URLS
            print(f"📋 Using first {len(seed_urls)} of {len(DEFAULT_SEED_URLS)} generated NYC seed URLs", flush=True)
        except ValueError:
            # First arg is a URL (or not a number)
            seed_urls = sys.argv[1:]
            print(f"📋 Using {len(seed_urls)} manually provided seed URL(s)", flush=True)
    else:
        # Use all auto-generated NYC seed URLs
        seed_urls = DEFAULT_SEED_URLS
        print(f"📋 Generated {len(seed_urls)} NYC seed URLs using Neighborhood + Intent strategy", flush=True)
        print(f"  Example URLs:", flush=True)
        for i, url in enumerate(seed_urls[:3], 1):
            print(f"    {i}. {url}", flush=True)
        if len(seed_urls) > 3:
            print(f"    ... and {len(seed_urls) - 3} more", flush=True)
        print(f"\n  💡 Tip: Limit URLs by running: python scout_lemon8.py 50", flush=True)
    sys.stdout.flush()
    
    if not seed_urls:
        print("✗ No seed URLs available!", flush=True)
        sys.stdout.flush()
        sys.exit(1)
    
    # Check Supabase connection
    print("\n🔍 Checking Supabase connection...", flush=True)
    sys.stdout.flush()
    stats = get_queue_stats()
    if stats:
        print(f"📊 Current Queue Stats:", flush=True)
        print(f"  Pending: {stats.get('pending', 0)}", flush=True)
        print(f"  Processing: {stats.get('processing', 0)}", flush=True)
        print(f"  Completed: {stats.get('completed', 0)}", flush=True)
        print(f"  Failed: {stats.get('failed', 0)}", flush=True)
        sys.stdout.flush()
    else:
        print("⚠ Warning: Could not connect to Supabase. Check your credentials.", flush=True)
        sys.stdout.flush()
        # Always exit in CI - never prompt for input
        if is_ci:
            print("⚠ Running in CI environment - exiting due to Supabase connection failure", flush=True)
            print("⚠ Make sure SUPABASE_URL and SUPABASE_KEY are set as GitHub Secrets", flush=True)
            print("⚠ Also check that there are no extra spaces or newlines in the secret values", flush=True)
            sys.stdout.flush()
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
    print("\n🔍 Checking for Brave browser...", flush=True)
    sys.stdout.flush()
    brave_path = find_brave_path()
    if brave_path:
        print(f"✓ Found Brave at: {brave_path}", flush=True)
    else:
        print("⚠ Brave not found, using system Chrome/Chromium", flush=True)
    sys.stdout.flush()
    
    # Setup driver with error handling
    print("\n🔧 Setting up Chrome driver...", flush=True)
    sys.stdout.flush()
    try:
        driver = setup_driver(brave_path)
        driver.set_page_load_timeout(30)
        print("✓ Driver setup complete, page load timeout set to 30s", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"\n✗ FATAL: Failed to setup driver: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.exit(1)
    
    total_discovered = 0
    
    try:
        print(f"\n🚀 Starting to process {len(seed_urls)} seed URLs...", flush=True)
        sys.stdout.flush()
        for idx, seed_url in enumerate(seed_urls, 1):
            print(f"\n{'='*60}", flush=True)
            print(f"Processing seed URL {idx}/{len(seed_urls)}: {seed_url}", flush=True)
            sys.stdout.flush()
            
            # Discover URLs from this seed
            urls = discover_article_urls(driver, seed_url, max_scrolls=50)
            
            if urls:
                # Extract hashtag from URL if possible
                source_hashtag = None
                if "hashtag" in seed_url or "experience" in seed_url:
                    source_hashtag = seed_url.split("/")[-1].split("?")[0]
                
                # Add to queue
                print(f"  Adding {len(urls)} URLs to queue...", flush=True)
                sys.stdout.flush()
                added = add_urls_to_queue(
                    urls=urls,
                    source_hashtag=source_hashtag,
                    source_url=seed_url
                )
                total_discovered += added
                print(f"  ✓ Added {added} new URLs to queue", flush=True)
                sys.stdout.flush()
                
                # Rate limiting - be respectful
                time.sleep(2)
            else:
                print(f"  ⚠ No URLs discovered from {seed_url}", flush=True)
                sys.stdout.flush()
        
        print(f"\n{'='*60}", flush=True)
        print(f"✓ Scout completed!", flush=True)
        print(f"  Total new URLs added to queue: {total_discovered}", flush=True)
        sys.stdout.flush()
        
        # Show updated stats
        stats = get_queue_stats()
        if stats:
            print(f"\n📊 Updated Queue Stats:", flush=True)
            print(f"  Pending: {stats.get('pending', 0)}", flush=True)
            print(f"  Processing: {stats.get('processing', 0)}", flush=True)
            print(f"  Completed: {stats.get('completed', 0)}", flush=True)
            print(f"  Failed: {stats.get('failed', 0)}", flush=True)
            sys.stdout.flush()
        
    except KeyboardInterrupt:
        print("\n\n⚠ Scout interrupted by user.", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
    finally:
        print("\n🔧 Closing browser...", flush=True)
        sys.stdout.flush()
        try:
            driver.quit()
            print("✓ Browser closed.", flush=True)
        except:
            print("⚠ Error closing browser (may already be closed)", flush=True)
        sys.stdout.flush()

if __name__ == "__main__":
    main()
