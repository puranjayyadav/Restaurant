"""
Yelp URL Enricher - The Sniper Strategy (Method 1)
===================================================

Best for: Filling in the gaps for restaurants you already have from Google Maps.
Philosophy: "Don't search Yelp. Search for Yelp."

Instead of attacking Yelp's search bar (which is heavily defended), you use a public 
search engine (like DuckDuckGo or Google) to find the Yelp URL for you. Search engines 
have already indexed Yelp, so you are essentially querying their index.

The Architecture:
1. Input: Read a row from your places table (e.g., "Carbone, New York")
2. The Proxy: Send a query to DuckDuckGo: site:yelp.com/biz "Carbone" "New York"
3. Extraction: Grab the first result. It will almost always be the correct Yelp business page.
4. Save: Store that URL in your database.
5. Scrape (Later): Now that you have the direct link, you can visit that specific page 
   later to get the rating/price, which triggers fewer alarms than running a search on Yelp.
"""

import os
import sys
import time
import urllib.parse
import re
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import django

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'my_new_project'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from res_backend.models import ScrapedRestaurant


def setup_chromium_driver(headless: bool = True):
    """
    Setup Selenium WebDriver with Chromium/Chrome.
    
    Args:
        headless: Whether to run browser in headless mode
    
    Returns:
        WebDriver instance
    """
    options = Options()
    
    # Anti-detection measures
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if headless:
        options.add_argument('--headless')
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    try:
        driver = webdriver.Chrome(options=options)
        # Execute script to hide webdriver property
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        return driver
    except Exception as e:
        print(f"ERROR: Failed to create Chromium driver: {e}")
        raise


def search_yelp_url_duckduckgo(restaurant_name: str, city: str, state: str = None, driver: webdriver.Chrome = None) -> Optional[str]:
    """
    Search for Yelp URL using DuckDuckGo search engine with Selenium.
    
    Args:
        restaurant_name: Name of the restaurant
        city: City where the restaurant is located
        state: Optional state abbreviation
        driver: Optional WebDriver instance (will create one if not provided)
    
    Returns:
        Yelp URL if found, None otherwise
    """
    should_close_driver = driver is None
    
    try:
        if driver is None:
            driver = setup_chromium_driver(headless=True)
        
        # Build simple search query: "Restaurant Name Yelp City"
        query = f"{restaurant_name} Yelp {city}"
        if state:
            query += f" {state}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        # Navigate to search page
        driver.get(url)
        time.sleep(3)  # Wait for page to load (increased for reliability)
        
        # Try to find result links - DuckDuckGo uses various selectors
        yelp_pattern = r'https?://(?:www\.)?yelp\.com/biz/[^\s"<>]+'
        
        # Method 1: Look for links with class "result__a"
        try:
            result_links = driver.find_elements(By.CSS_SELECTOR, 'a.result__a')
            for link in result_links:
                href = link.get_attribute('href')
                if href and 'yelp.com/biz/' in href:
                    yelp_url = href.split('?')[0]
                    if yelp_url.startswith('http'):
                        return yelp_url
        except:
            pass
        
        # Method 2: Look for all links and check for Yelp URLs
        try:
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            for link in all_links:
                href = link.get_attribute('href')
                if href and 'yelp.com/biz/' in href:
                    yelp_url = href.split('?')[0]
                    if yelp_url.startswith('http'):
                        return yelp_url
        except:
            pass
        
        # Method 3: Regex search in page source
        page_source = driver.page_source
        matches = re.findall(yelp_pattern, page_source)
        if matches:
            yelp_url = matches[0].split('?')[0].split('"')[0].split("'")[0]
            if yelp_url.startswith('http'):
                return yelp_url
        
        return None
        
    except Exception as e:
        print(f"ERROR: DuckDuckGo search failed for '{restaurant_name}': {e}")
        return None
    finally:
        if should_close_driver and driver:
            driver.quit()


def search_yelp_url_google(restaurant_name: str, city: str, state: str = None, driver: webdriver.Chrome = None) -> Optional[str]:
    """
    Fallback: Search for Yelp URL using Google search engine with Selenium.
    
    Args:
        restaurant_name: Name of the restaurant
        city: City where the restaurant is located
        state: Optional state abbreviation
        driver: Optional WebDriver instance (will create one if not provided)
    
    Returns:
        Yelp URL if found, None otherwise
    """
    should_close_driver = driver is None
    
    try:
        if driver is None:
            driver = setup_chromium_driver(headless=True)
        
        # Build simple search query: "Restaurant Name Yelp City"
        query = f"{restaurant_name} Yelp {city}"
        if state:
            query += f" {state}"
        encoded_query = urllib.parse.quote(query)
        
        # Google search URL
        url = f"https://www.google.com/search?q={encoded_query}"
        
        # Navigate to search page
        driver.get(url)
        time.sleep(3)  # Wait for page to load (increased for reliability)
        
        yelp_pattern = r'https?://(?:www\.)?yelp\.com/biz/[^\s"<>]+'
        
        # Method 1: Look for result links
        try:
            # Google result links are typically in divs with class "g" or similar
            result_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="yelp.com/biz"]')
            for link in result_links:
                href = link.get_attribute('href')
                if href and 'yelp.com/biz/' in href:
                    # Google may use /url?q= redirects
                    if '/url?q=' in href:
                        actual_url = urllib.parse.unquote(href.split('/url?q=')[1].split('&')[0])
                    else:
                        actual_url = href
                    
                    if 'yelp.com/biz/' in actual_url:
                        yelp_url = actual_url.split('?')[0]
                        if yelp_url.startswith('http'):
                            return yelp_url
        except:
            pass
        
        # Method 2: Look for all links
        try:
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            for link in all_links:
                href = link.get_attribute('href')
                if href and 'yelp.com/biz/' in href:
                    if '/url?q=' in href:
                        actual_url = urllib.parse.unquote(href.split('/url?q=')[1].split('&')[0])
                    else:
                        actual_url = href
                    
                    if 'yelp.com/biz/' in actual_url:
                        yelp_url = actual_url.split('?')[0]
                        if yelp_url.startswith('http'):
                            return yelp_url
        except:
            pass
        
        # Method 3: Regex search in page source
        page_source = driver.page_source
        matches = re.findall(yelp_pattern, page_source)
        if matches:
            yelp_url = matches[0].split('?')[0].split('"')[0].split("'")[0]
            if yelp_url.startswith('http'):
                return yelp_url
        
        return None
        
    except Exception as e:
        print(f"ERROR: Google search failed for '{restaurant_name}': {e}")
        return None
    finally:
        if should_close_driver and driver:
            driver.quit()


def find_yelp_url(restaurant_name: str, city: str, state: str = None, debug: bool = False) -> Optional[str]:
    """
    Find Yelp URL using search engines. Tries DuckDuckGo first, then Google as fallback.
    Reuses the same WebDriver instance for efficiency.
    
    Args:
        restaurant_name: Name of the restaurant
        city: City where the restaurant is located
        state: Optional state abbreviation
        debug: Whether to print debug information
    
    Returns:
        Yelp URL if found, None otherwise
    """
    driver = None
    try:
        # Create a single driver instance to reuse
        driver = setup_chromium_driver(headless=True)
        
        # Try DuckDuckGo first (more privacy-friendly, less likely to block)
        print(f"Searching DuckDuckGo for: {restaurant_name}, {city}, {state or ''}")
        yelp_url = search_yelp_url_duckduckgo(restaurant_name, city, state, driver=driver)
        
        if yelp_url:
            print(f"✓ Found Yelp URL via DuckDuckGo: {yelp_url}")
            return yelp_url
        
        # Fallback to Google (reuse same driver)
        print(f"Trying Google search for: {restaurant_name}, {city}, {state or ''}")
        yelp_url = search_yelp_url_google(restaurant_name, city, state, driver=driver)
        
        if yelp_url:
            print(f"✓ Found Yelp URL via Google: {yelp_url}")
            return yelp_url
        
        print(f"✗ Could not find Yelp URL for: {restaurant_name}, {city}, {state or ''}")
        return None
    finally:
        if driver:
            driver.quit()


def enrich_restaurant_with_yelp_url(restaurant: ScrapedRestaurant, delay: float = 1.0) -> bool:
    """
    Enrich a single restaurant record with its Yelp URL.
    
    Args:
        restaurant: ScrapedRestaurant instance
        delay: Delay between requests (in seconds) to avoid rate limiting
    
    Returns:
        True if URL was found and saved, False otherwise
    """
    # Skip if already has Yelp URL
    if restaurant.source_url and 'yelp.com' in restaurant.source_url:
        print(f"Skipping {restaurant.name} - already has Yelp URL")
        return True
    
    # Skip if source is already Yelp
    if restaurant.source == 'yelp' and restaurant.source_url:
        print(f"Skipping {restaurant.name} - already from Yelp")
        return True
    
    # Build search query from restaurant data
    restaurant_name = restaurant.name
    city = restaurant.city
    state = restaurant.state
    
    if not restaurant_name or not city:
        print(f"Skipping {restaurant.id} - missing name or city")
        return False
    
    # Search for Yelp URL
    yelp_url = find_yelp_url(restaurant_name, city, state, debug=False)
    
    if yelp_url:
        # Save the URL
        # If this is a Google Maps restaurant, we can either:
        # 1. Update the existing record with Yelp URL in source_url
        # 2. Create a new ScrapedRestaurant record with source='yelp'
        # For now, we'll update the existing record's source_url if it's empty,
        # or store it in raw_data for reference
        
        if not restaurant.source_url:
            restaurant.source_url = yelp_url
        else:
            # Store Yelp URL in raw_data if source_url is already used
            if not restaurant.raw_data:
                restaurant.raw_data = {}
            restaurant.raw_data['yelp_url'] = yelp_url
        
        restaurant.save()
        print(f"✓ Saved Yelp URL for {restaurant.name}")
        
        # Add delay to avoid rate limiting
        time.sleep(delay)
        return True
    else:
        # Add delay even on failure to maintain consistent rate
        time.sleep(delay)
        return False


def enrich_all_restaurants(
    source: str = 'google',
    limit: Optional[int] = None,
    city_filter: Optional[str] = None,
    state_filter: Optional[str] = None,
    delay: float = 2.0
) -> Dict[str, int]:
    """
    Enrich all restaurants (or a filtered subset) with Yelp URLs.
    
    Args:
        source: Filter by source (e.g., 'google' for Google Maps restaurants)
        limit: Maximum number of restaurants to process (None for all)
        city_filter: Only process restaurants in this city
        state_filter: Only process restaurants in this state
        delay: Delay between requests (in seconds)
    
    Returns:
        Dictionary with statistics: {'processed': int, 'found': int, 'failed': int}
    """
    # Query restaurants
    queryset = ScrapedRestaurant.objects.filter(is_active=True)
    
    if source:
        queryset = queryset.filter(source=source)
    
    if city_filter:
        queryset = queryset.filter(city__icontains=city_filter)
    
    if state_filter:
        queryset = queryset.filter(state__iexact=state_filter)
    
    # Filter out restaurants that already have Yelp URLs
    queryset = queryset.exclude(
        source='yelp'
    ).exclude(
        source_url__icontains='yelp.com'
    )
    
    if limit:
        queryset = queryset[:limit]
    
    total = queryset.count()
    print(f"\n{'='*60}")
    print(f"Yelp URL Enricher - Processing {total} restaurants")
    print(f"Filters: source={source}, city={city_filter}, state={state_filter}")
    print(f"{'='*60}\n")
    
    if total == 0:
        print("WARNING: No restaurants found matching the criteria.")
        print("Checking what restaurants exist in database...")
        sample = ScrapedRestaurant.objects.filter(is_active=True)[:5]
        if sample.exists():
            print("\nSample restaurants in database:")
            for r in sample:
                print(f"  - {r.name} | Source: {r.source} | City: {r.city} | State: {r.state} | Has Yelp URL: {'Yes' if (r.source_url and 'yelp.com' in r.source_url) else 'No'}")
        else:
            print("  No restaurants found in database at all.")
        print()
    
    stats = {'processed': 0, 'found': 0, 'failed': 0}
    
    for idx, restaurant in enumerate(queryset, 1):
        print(f"\n[{idx}/{total}] Processing: {restaurant.name} ({restaurant.city}, {restaurant.state})")
        
        try:
            success = enrich_restaurant_with_yelp_url(restaurant, delay=delay)
            stats['processed'] += 1
            
            if success:
                stats['found'] += 1
            else:
                stats['failed'] += 1
                
        except Exception as e:
            print(f"ERROR: Failed to process {restaurant.name}: {e}")
            stats['processed'] += 1
            stats['failed'] += 1
            time.sleep(delay)  # Still delay on error
    
    print(f"\n{'='*60}")
    print(f"Enrichment Complete!")
    print(f"Processed: {stats['processed']}")
    print(f"Found Yelp URLs: {stats['found']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success Rate: {(stats['found']/stats['processed']*100) if stats['processed'] > 0 else 0:.1f}%")
    print(f"{'='*60}\n")
    
    return stats


def main():
    """
    Main entry point for the script.
    Can be run from command line with optional arguments.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Enrich restaurant database with Yelp URLs using search engines'
    )
    parser.add_argument(
        '--source',
        type=str,
        default='google',
        help='Filter by source (default: google)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of restaurants to process (default: all)'
    )
    parser.add_argument(
        '--city',
        type=str,
        default=None,
        help='Filter by city (case-insensitive)'
    )
    parser.add_argument(
        '--state',
        type=str,
        default=None,
        help='Filter by state (case-insensitive)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: process only one restaurant'
    )
    
    args = parser.parse_args()
    
    if args.test:
        # Test mode: process one restaurant
        restaurant = ScrapedRestaurant.objects.filter(
            is_active=True,
            source=args.source
        ).exclude(
            source='yelp'
        ).exclude(
            source_url__icontains='yelp.com'
        ).first()
        
        if restaurant:
            print(f"Test mode: Processing {restaurant.name}")
            enrich_restaurant_with_yelp_url(restaurant, delay=args.delay)
        else:
            print("No restaurant found for testing")
    else:
        # Process all matching restaurants
        enrich_all_restaurants(
            source=args.source,
            limit=args.limit,
            city_filter=args.city,
            state_filter=args.state,
            delay=args.delay
        )


if __name__ == '__main__':
    main()

