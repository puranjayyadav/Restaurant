"""
Scrape restaurant links from OpenTable search results page with pagination
"""
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def scrape_single_page(driver, page_num):
    """
    Scrape restaurant links from a single page
    Returns list of restaurant dictionaries
    """
    print(f"\n{'='*60}")
    print(f"Scraping Page {page_num}")
    print(f"{'='*60}")
    
    restaurant_links = []
    links_found = set()
    
    # Wait for page to load and content to appear
    print("Waiting for page content to load...")
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        print("Page took too long to load")
    
    time.sleep(10)  # Wait longer for dynamic content to load
    
    # Try to interact with page to trigger loading
    try:
        # Click on map view toggle if it exists (sometimes shows more results)
        map_toggle = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='map'], button[data-testid*='map']")
        if map_toggle:
            map_toggle[0].click()
            time.sleep(3)
    except:
        pass
    
    # Scroll slowly to the end of the page to load all restaurants
    print("Scrolling slowly to the end of the page to load all restaurants...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    # Hard cap: never scroll more than 50 times on a page
    max_scrolls = 50
    consecutive_no_change = 0
    reached_bottom = False
    
    while scroll_attempts < max_scrolls and not reached_bottom:
        # Get current scroll position
        current_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
        page_height = driver.execute_script("return document.body.scrollHeight")
        
        # Check if we're already at or near the bottom before scrolling
        at_bottom_before = (current_scroll + 100) >= page_height
        
        if at_bottom_before:
            # Already at bottom, check if new content loads
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            new_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
            
            if new_height == page_height:
                # No new content loaded, we're truly at the bottom
                consecutive_no_change += 1
                if consecutive_no_change >= 2:
                    print(f"  Reached bottom of page (no new content after {consecutive_no_change} checks)")
                    reached_bottom = True
                    break
            else:
                # New content loaded, continue scrolling
                last_height = new_height
                consecutive_no_change = 0
                print(f"  Scrolled to position {int(new_scroll)}/{int(new_height)} - New content loaded!")
        else:
            # Scroll down slowly in small increments
            scroll_increment = 300
            target_scroll = min(current_scroll + scroll_increment, page_height)
            
            driver.execute_script(f"window.scrollTo(0, {target_scroll});")
            time.sleep(1.5)
            
            # Check if we've reached the bottom after scrolling
            new_height = driver.execute_script("return document.body.scrollHeight")
            new_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
            at_bottom_after = (new_scroll + 100) >= new_height
            
            # Check if page height changed
            if new_height > last_height:
                print(f"  Scrolled to position {int(new_scroll)}/{int(new_height)} - New content loaded!")
                last_height = new_height
                consecutive_no_change = 0
            else:
                consecutive_no_change += 1
                if scroll_attempts % 10 == 0:
                    print(f"  Scrolled to position {int(new_scroll)}/{int(new_height)} (Total scrolls: {scroll_attempts + 1})")
            
            # If at bottom and no new content for a while, we're done
            if at_bottom_after:
                if consecutive_no_change >= 2:
                    print(f"  Reached bottom of page.")
                    reached_bottom = True
                    break
        
        scroll_attempts += 1
        
        # Count current links periodically
        if scroll_attempts % 5 == 0:
            current_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/r/']")
            unique_urls = set()
            for link in current_links:
                href = link.get_attribute('href')
                if href and '/r/' in href:
                    clean_url = href.split('?')[0].split('#')[0]
                    if '#reviews' not in clean_url and '#photos' not in clean_url:
                        unique_urls.add(clean_url)
            print(f"    Found {len(unique_urls)} unique restaurant links so far...")
    
    if not reached_bottom:
        # One final check to ensure we're at the bottom
        print("  Performing final scroll to bottom...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
    
    # Extract restaurant links using JavaScript
    print("Extracting restaurant links...")
    js_links = driver.execute_script("""
        var links = [];
        var seenUrls = new Set();
        var allLinks = document.querySelectorAll('a[href*="/r/"]');
        for (var i = 0; i < allLinks.length; i++) {
            var link = allLinks[i];
            var href = link.href || link.getAttribute('href');
            if (!href) continue;
            
            if (href.startsWith('//')) href = 'https:' + href;
            if (href.startsWith('/')) href = 'https://www.opentable.com' + href;
            
            var cleanUrl = href.split('?')[0].split('#')[0];
            
            if (cleanUrl.includes('#reviews') || cleanUrl.includes('#photos') || !cleanUrl.includes('/r/') || seenUrls.has(cleanUrl)) {
                continue;
            }
            seenUrls.add(cleanUrl);
            
            var name = (link.textContent || link.innerText || '').trim();
            
            if (!name || name.length < 3) {
                var parent = link;
                for (var j = 0; j < 5 && parent; j++) {
                    parent = parent.parentElement;
                    if (parent) {
                        var parentText = (parent.textContent || '').trim();
                        var firstLine = parentText.split('\\n')[0].trim();
                        if (firstLine && firstLine.length > 3 && firstLine.length < 100 && 
                            !firstLine.match(/^[0-9$()]+$/) && 
                            !firstLine.toLowerCase().includes('booked') &&
                            !firstLine.toLowerCase().includes('price')) {
                            name = firstLine;
                            break;
                        }
                    }
                }
            }
            
            if (!name || name.length < 3) {
                var urlParts = cleanUrl.split('/r/');
                if (urlParts.length > 1) {
                    var slug = urlParts[1].split('?')[0].split('#')[0];
                    name = slug.replace(/-/g, ' ').replace(/\\b\\w/g, function(l) { return l.toUpperCase(); });
                }
            }
            
            if (name) {
                name = name.replace(/^(Icon|Promoted|Exceptional|Awesome)\\s*/i, '');
                name = name.split('\\n')[0].substring(0, 50).trim();
            }
            
            links.push({
                name: name || 'Unknown Restaurant',
                url: cleanUrl,
                opentable_id: cleanUrl.split('/r/')[1] ? cleanUrl.split('/r/')[1].split('?')[0].split('#')[0] : null
            });
        }
        return links;
    """)
    
    # Process JavaScript-extracted links
    for link_data in js_links:
        clean_url = link_data['url']
        if clean_url and '/r/' in clean_url and clean_url not in links_found:
            name = link_data.get('name', '')
            if name:
                name = re.sub(r'\d+\.\d+', '', name)
                parts = re.split(r'[\n•]|Promoted|Exceptional|Awesome|Booked|Price:|Moderate|Expensive|Very Expensive', name)
                for part in parts:
                    part = part.strip()
                    if (part and len(part) > 2 
                        and not part.startswith('(') 
                        and not part.startswith('$')
                        and not part.isdigit()
                        and part.lower() not in ['promoted', 'exceptional', 'awesome', 'booked', 'price', 'moderate', 'expensive', 'very expensive', 'icon', 'seating options', 'times today', 'pts', 'pm', 'am']):
                        name = part
                        break
                
                if not name or len(name) < 3:
                    url_parts = clean_url.split('/r/')
                    if len(url_parts) > 1:
                        name = url_parts[1].split('?')[0].split('#')[0].replace('-', ' ').title()
            
            restaurant_data = {
                'name': name,
                'url': clean_url,
                'opentable_id': link_data.get('opentable_id')
            }
            links_found.add(clean_url)
            restaurant_links.append(restaurant_data)
            print(f"    Found: {name}")
    
    # Remove duplicates
    seen_urls = set()
    unique_links = []
    for link in restaurant_links:
        url = link['url']
        if '#reviews' in url or '#photos' in url or '/r/' not in url:
            continue
        
        clean_url = url.split('#')[0].split('?')[0]
        if clean_url not in seen_urls:
            seen_urls.add(clean_url)
            link['url'] = clean_url
            if link['name']:
                link['name'] = ' '.join(link['name'].split())
            unique_links.append(link)
    
    restaurant_links = unique_links
    restaurant_links.sort(key=lambda x: x['name'])
    
    print(f"\nPage {page_num} complete: Found {len(restaurant_links)} unique restaurant links")
    return restaurant_links


def scrape_opentable_links(url, output_file='opentable_restaurant_links.json', max_pages=12):
    """
    Scrape all restaurant links from OpenTable search results pages (with pagination)
    Only adds restaurants that haven't been recorded previously
    """
    print(f"Starting to scrape OpenTable pages (up to page {max_pages})")
    print(f"Initial URL: {url}")
    
    # Load existing restaurants to avoid duplicates
    existing_restaurants = []
    existing_urls = set()
    existing_ids = set()
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            existing_restaurants = json.load(f)
            for restaurant in existing_restaurants:
                if 'url' in restaurant:
                    clean_url = restaurant['url'].split('#')[0].split('?')[0]
                    existing_urls.add(clean_url)
                if 'opentable_id' in restaurant and restaurant['opentable_id']:
                    existing_ids.add(restaurant['opentable_id'])
        print(f"Loaded {len(existing_restaurants)} existing restaurants from {output_file}")
        print(f"Will skip restaurants that already exist (by URL or ID)")
    except FileNotFoundError:
        print(f"No existing file found at {output_file}. Starting fresh.")
    except json.JSONDecodeError:
        print(f"Error reading {output_file}. Starting fresh.")
    
    # Setup Chrome options
    options = Options()
    options.headless = True
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    
    all_restaurant_links = existing_restaurants.copy()  # Start with existing restaurants
    all_seen_urls = existing_urls.copy()  # Track all URLs (existing + new)
    
    try:
        print("Loading initial page...")
        driver.get(url)
        time.sleep(5)
        
        # Scrape pages 1 through max_pages
        for page_num in range(1, max_pages + 1):
            # Scrape current page
            page_links = scrape_single_page(driver, page_num)
            
            # Add unique links from this page to the master list (only if not already exists)
            new_restaurants_count = 0
            for link in page_links:
                clean_url = link['url']
                restaurant_id = link.get('opentable_id')
                
                # Check if restaurant already exists (by URL or ID)
                url_exists = clean_url in existing_urls or clean_url in all_seen_urls
                id_exists = restaurant_id and (restaurant_id in existing_ids)
                
                if not url_exists and not id_exists:
                    all_seen_urls.add(clean_url)
                    if restaurant_id:
                        existing_ids.add(restaurant_id)
                    all_restaurant_links.append(link)
                    new_restaurants_count += 1
                else:
                    print(f"    Skipped duplicate: {link.get('name', 'Unknown')} (already exists)")
            
            print(f"\nPage {page_num}: Found {new_restaurants_count} new restaurants (skipped {len(page_links) - new_restaurants_count} duplicates)")
            print(f"Total unique restaurants collected so far: {len(all_restaurant_links)} ({len(all_restaurant_links) - len(existing_restaurants)} new)")
            
            # Save progress after each page (in case of crash)
            all_restaurant_links_sorted = sorted(all_restaurant_links, key=lambda x: x['name'])
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_restaurant_links_sorted, f, indent=2, ensure_ascii=False)
            print(f"  Progress saved to {output_file} ({len(all_restaurant_links)} restaurants)")
            
            # If not the last page, navigate to next page
            if page_num < max_pages:
                print(f"\nNavigating to page {page_num + 1}...")
                
                next_page_found = False
                
                # Try to find pagination button
                try:
                    pagination_links = driver.find_elements(By.CSS_SELECTOR, 
                        "a[class*='ojKcSDzr190-'], a[aria-label*='Go to page'], a[aria-label*='page number']")
                    
                    for link in pagination_links:
                        try:
                            aria_label = link.get_attribute('aria-label') or ''
                            link_text = link.text.strip()
                            
                            if (f'page number {page_num + 1}' in aria_label.lower() or 
                                link_text == str(page_num + 1)):
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", link)
                                time.sleep(2)
                                driver.execute_script("arguments[0].click();", link)
                                print(f"  Clicked pagination button for page {page_num + 1}")
                                next_page_found = True
                                time.sleep(5)
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"  Error finding pagination: {e}")
                
                # Try JavaScript click if not found
                if not next_page_found:
                    try:
                        next_page_clicked = driver.execute_script(f"""
                            var links = document.querySelectorAll('a[aria-label*="page number {page_num + 1}"], a[aria-label*="Go to page number {page_num + 1}"]');
                            for (var i = 0; i < links.length; i++) {{
                                var link = links[i];
                                var ariaLabel = link.getAttribute('aria-label') || '';
                                var linkText = link.textContent.trim();
                                if (ariaLabel.includes('{page_num + 1}') || linkText === '{page_num + 1}') {{
                                    link.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                    link.click();
                                    return true;
                                }}
                            }}
                            return false;
                        """)
                        
                        if next_page_clicked:
                            print(f"  Clicked pagination button for page {page_num + 1} (via JavaScript)")
                            time.sleep(5)
                            next_page_found = True
                    except Exception as e:
                        print(f"  Error with JavaScript pagination click: {e}")
                
                if not next_page_found:
                    print(f"  WARNING: Could not find pagination button for page {page_num + 1}")
                    time.sleep(3)
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total unique restaurant links found across all pages: {len(all_restaurant_links)}")
        
        # Sort all links by name
        all_restaurant_links.sort(key=lambda x: x['name'])
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_restaurant_links, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(all_restaurant_links)} restaurant links to {output_file}")
        
        return all_restaurant_links
        
    except Exception as e:
        print(f"Error scraping pages: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        driver.quit()


if __name__ == "__main__":
    url = "https://www.opentable.com/s?dateTime=2025-12-04T19%3A00%3A00&covers=2&metroId=8&shouldUseLatLongSearch=false&originCorrelationId=5ead2829-976d-4f21-8fa2-0e1c9c102e1c&corrid=c6c4a20d-85c0-43c1-81ca-e213793c77b4&queryUnderstandingType=none&showMap=true&sortBy=web_conversion"
    
    # Load existing count before scraping
    try:
        with open('opentable_restaurant_links.json', 'r', encoding='utf-8') as f:
            existing_count = len(json.load(f))
    except:
        existing_count = 0
    
    links = scrape_opentable_links(url, 'opentable_restaurant_links.json', max_pages=12)
    new_count = len(links) - existing_count
    print(f"\nScraping complete! Total restaurants: {len(links)} ({new_count} new restaurants added)")

