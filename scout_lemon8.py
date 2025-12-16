"""Scout: Discovers Lemon8 article URLs and adds them to Supabase queue"""
import os
import sys
import json
import time
import requests
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from urllib.parse import urljoin, quote

# Force unbuffered output for CI environments
if os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true":
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

print("=" * 60, flush=True)
print("SCRIPT STARTED - scout_lemon8.py", flush=True)
print("=" * 60, flush=True)
sys.stdout.flush()

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Supabase Imports
print("Importing supabase_config...", flush=True)
from supabase_config import add_urls_to_queue, get_queue_stats, get_processed_seed_urls
print("All imports successful", flush=True)

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ============================================================================
# DYNAMIC CITY RESEARCHER (The "Brain")
# ============================================================================

def fetch_location_strategy(location_name):
    """
    Uses LLM to determine if the input is a City or a Region.
    If Region -> Returns list of major cities to expand.
    If City -> Returns the Vibe Map (neighborhoods, foods, landmarks).
    """
    print(f"\n🧠 Analyzing location: {location_name}...", flush=True)
    
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠ No API Key. Using fallback.", flush=True)
        return {"type": "city", "neighborhoods": ["Downtown"], "local_foods": ["food"], "landmarks": []}

    prompt = f"""
    I am building a travel guide for "{location_name}".
    
    Determine if this is a SPECIFIC CITY (like "Austin", "Brooklyn") or a BROAD REGION/STATE (like "California", "Texas", "USA", "Italy").
    
    RETURN JSON ONLY:
    
    CASE A: It is a REGION/STATE:
    {{
        "type": "region",
        "target_cities": ["List", "of", "top", "3-5", "major", "cities", "in", "this", "region"]
    }}
    
    CASE B: It is a SPECIFIC CITY:
    {{
        "type": "city",
        "neighborhoods": ["List of 8-10 cool/trendy neighborhoods"],
        "local_foods": ["List of 5 iconic local dishes"],
        "landmarks": ["List of 5 instagrammable spots"]
    }}
    """

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            profile = json.loads(content)
            return profile
            
        else:
            print(f"❌ LLM Error {response.status_code}: {response.text}", flush=True)
            
    except Exception as e:
        print(f"❌ LLM Exception: {e}", flush=True)

    # Fallback if LLM fails
    return {"type": "city", "neighborhoods": [], "local_foods": [], "landmarks": []}

def generate_seed_urls_recursive(location_name):
    """
    Recursively generates URLs. 
    If location is 'California', it auto-expands to 'Los Angeles', 'San Francisco', etc.
    """
    strategy = fetch_location_strategy(location_name)
    all_urls = []
    
    if strategy.get("type") == "region":
        cities = strategy.get("target_cities", [])
        print(f"🌎 Region detected! Auto-expanding to cities: {cities}", flush=True)
        
        for city in cities:
            # Recursive call for each city
            print(f"  > Expanding city: {city}...", flush=True)
            city_urls = generate_seed_urls_recursive(city)
            all_urls.extend(city_urls)
            time.sleep(1) # Be nice to the API
            
    else:
        # It's a city, generate URLs normally
        print(f"🏙️  City detected. Generating Vibe Map for {location_name}...", flush=True)
        profile = strategy # The strategy itself is the city profile here
        print(f"   Full Profile for {location_name}: {json.dumps(profile, indent=2)}", flush=True)
        urls = generate_seed_urls_from_profile(location_name, profile)
        all_urls.extend(urls)
        
    return list(set(all_urls))

def generate_seed_urls_from_profile(city_name, profile):
    """Generates actual URLs from a city profile"""
    base_url = "https://www.lemon8-app.com/discover/"
    all_urls = []
    
    intents = ["restaurants", "bars", "coffee shops", "aesthetic", "hidden gems", "shopping"]
    
    # 1. Neighborhoods
    for hood in profile.get('neighborhoods', []):
        for intent in intents:
            query = f"{hood} {city_name} {intent}"
            all_urls.append(f"{base_url}{quote(query)}?region=us")
            
    # 2. Foods
    for food in profile.get('local_foods', []):
        query = f"best {food} in {city_name}"
        all_urls.append(f"{base_url}{quote(query)}?region=us")
        
    # 3. Mega Keywords
    mega_templates = [
        f"3 days in {city_name} itinerary",
        f"{city_name} weekend trip guide",
        f"non touristy things to do in {city_name}",
        f"best speakeasies in {city_name}",
        f"instagrammable places in {city_name}"
    ]
    
    for keyword in mega_templates:
        all_urls.append(f"{base_url}{quote(keyword)}?region=us")
        
    return all_urls

# ============================================================================
# BROWSER & SCRAPING UTILS
# ============================================================================

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
    
    is_ci = os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true"
    options = Options()
    options.add_argument('--headless=new')
    
    if brave_path and os.path.exists(brave_path):
        options.binary_location = brave_path
        print(f"Using Brave browser at: {brave_path}", flush=True)
    else:
        options.binary_location = "/usr/bin/chromium-browser" if is_ci else None
        print("Using system Chrome/Chromium", flush=True)
    
    # Anti-detection
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if is_ci:
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
    
    print("Creating WebDriver instance...", flush=True)
    try:
        if is_ci:
            from selenium.webdriver.chrome.service import Service
            service = Service()
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"✗ Failed to create WebDriver: {e}", flush=True)
        raise

def auto_scroll(driver, scroll_pause_time=0.5, max_scrolls=100):
    """Smoothly scroll down the page to load dynamic content"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0
    no_change_count = 0
    
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollBy({top: 300, behavior: 'smooth'});")
        scroll_count += 1
        time.sleep(scroll_pause_time)
        time.sleep(0.3)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            no_change_count += 1
            if no_change_count >= 3:
                driver.execute_script("window.scrollBy({top: 1000, behavior: 'smooth'});")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                no_change_count = 0
        else:
            no_change_count = 0
        
        last_height = new_height
        if scroll_count % 10 == 0:
            print(f"  Scrolled {scroll_count} times...", flush=True)
            
    return scroll_count

def is_valid_article_url(url):
    """Check if URL is a valid article URL matching pattern: /@username/number?region=us"""
    import re
    if not url: return False
    pattern = r'/@[^/]+/\d+\?region=us'
    return bool(re.search(pattern, url))

def discover_article_urls(driver, seed_url, max_scrolls=100):
    """Discover article URLs from a seed URL"""
    print(f"\n🔍 Discovering URLs from: {seed_url}", flush=True)
    
    try:
        driver.get(seed_url)
        time.sleep(3)
        auto_scroll(driver, scroll_pause_time=0.5, max_scrolls=max_scrolls)
        
        article_links = []
        base_url = "https://www.lemon8-app.com"
        seen_links = set()
        
        # Selectors to try
        selectors = ["a.article-recommend-card", "a.discover-immersive-article"]
        
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                try:
                    href = el.get_attribute("href")
                    if href:
                        full_url = urljoin(base_url, href)
                        if is_valid_article_url(full_url) and full_url not in seen_links:
                            seen_links.add(full_url)
                            article_links.append(full_url)
                except: continue
        
        # Check immersive container if it exists
        try:
            container = driver.find_element(By.ID, "immersive-posts")
            links = container.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href:
                        full_url = urljoin(base_url, href)
                        if is_valid_article_url(full_url) and full_url not in seen_links:
                            seen_links.add(full_url)
                            article_links.append(full_url)
                except: continue
        except: pass

        print(f"  ✓ Discovered {len(article_links)} unique article URLs", flush=True)
        return article_links
        
    except Exception as e:
        print(f"  ✗ Error discovering URLs: {e}", flush=True)
        return []

def get_next_unprocessed_batch(all_urls, processed_urls, batch_size, start_index=0):
    unprocessed = []
    current_index = start_index
    while len(unprocessed) < batch_size and current_index < len(all_urls):
        url = all_urls[current_index]
        if url not in processed_urls:
            unprocessed.append(url)
        current_index += 1
    return unprocessed, current_index

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Lemon8 URL Discovery Scout")
    parser.add_argument("--city", type=str, help="City or Region to research and scrape (e.g. 'Austin', 'California')")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    parser.add_argument("--no-auto-batch", action="store_true", help="Disable auto-batching")
    parser.add_argument("manual_url", nargs="*", help="Direct URLs to scrape (optional)")
    
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("🌱 LEMON8 SCOUT - URL Discovery", flush=True)
    print("=" * 60, flush=True)

    # 1. Determine Seed URLs using recursive strategy
    seed_urls_to_check = []
    
    if args.manual_url:
        print(f"📋 Using {len(args.manual_url)} manually provided URLs", flush=True)
        seed_urls_to_check = args.manual_url
        
    elif args.city:
        print(f"🚀 Launching Scout for: {args.city}", flush=True)
        seed_urls_to_check = generate_seed_urls_recursive(args.city)
        print(f"📋 Total generated seed URLs: {len(seed_urls_to_check)}", flush=True)
        
    else:
        print("❌ Error: No city or manual URLs specified.", flush=True)
        print("💡 Usage: python scout_lemon8.py --city 'Austin' or --city 'California'", flush=True)
        sys.exit(1)

    if not seed_urls_to_check:
        print("✗ No seed URLs generated. Exiting.", flush=True)
        sys.exit(1)

    # 2. Check Database Connection
    stats = get_queue_stats()
    if not stats:
        print("⚠ Warning: Could not connect to Supabase.", flush=True)
        if os.getenv("CI") == "true": sys.exit(1)

    # 3. Setup Browser
    brave_path = find_brave_path()
    try:
        driver = setup_driver(brave_path)
    except Exception:
        sys.exit(1)

    # 4. Processing Loop
    processed_urls = get_processed_seed_urls()
    current_index = 0
    batch_number = 1
    total_discovered = 0
    all_discovered_urls = []
    
    try:
        while current_index < len(seed_urls_to_check):
            # Batching logic
            if not args.no_auto_batch:
                batch, new_index = get_next_unprocessed_batch(
                    seed_urls_to_check, processed_urls, args.batch_size, current_index
                )
                current_index = new_index
            else:
                batch, current_index = get_next_unprocessed_batch(
                    seed_urls_to_check, processed_urls, args.batch_size, 0
                )
                current_index = len(seed_urls_to_check) # Force exit after one batch

            if not batch:
                print(f"\n📊 Batch {batch_number}: All URLs already processed.", flush=True)
                if current_index >= len(seed_urls_to_check): break
                batch_number += 1
                continue

            print(f"\n📊 Batch {batch_number}: Processing {len(batch)} URLs", flush=True)
            
            for idx, seed_url in enumerate(batch, 1):
                print(f"\n[{idx}/{len(batch)}] Processing: {seed_url}", flush=True)
                urls = discover_article_urls(driver, seed_url)
                
                if urls:
                    all_discovered_urls.extend(urls)
                    # Extract hashtag for queue tagging
                    hashtag = seed_url.split("/")[-1].split("?")[0] if "discover" in seed_url else None
                    
                    added = add_urls_to_queue(urls, source_hashtag=hashtag, source_url=seed_url)
                    total_discovered += added
                    print(f"  ✓ Added {added} new URLs to queue", flush=True)
                    time.sleep(2)
                else:
                    print("  ⚠ No URLs found", flush=True)

            if args.no_auto_batch: break
            
            # Refresh processed list for next batch safety
            processed_urls = get_processed_seed_urls()
            batch_number += 1

    except KeyboardInterrupt:
        print("WARN: Interrupted by user", flush=True)
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
    finally:
        print(f"✓ Scout Completed. Total new URLs: {total_discovered}", flush=True)
        driver.quit()

if __name__ == "__main__":
    main()
