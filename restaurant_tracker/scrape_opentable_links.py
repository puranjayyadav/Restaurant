"""
Scrape restaurant links from OpenTable search results page
"""
import json
import time
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
    max_scrolls = 100  # Increased limit for very long pages
    no_change_count = 0
    consecutive_no_change = 0
    
    while scroll_attempts < max_scrolls:
        # Get current scroll position
        current_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
        page_height = driver.execute_script("return document.body.scrollHeight")
        
        # Scroll down slowly in small increments (simulating human behavior)
        scroll_increment = 300  # Scroll 300px at a time
        target_scroll = min(current_scroll + scroll_increment, page_height)
        
        driver.execute_script(f"window.scrollTo(0, {target_scroll});")
        time.sleep(1.5)  # Wait between scrolls
        
        # Check if we've reached the bottom
        new_height = driver.execute_script("return document.body.scrollHeight")
        new_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
        
        # Check if we're at the bottom (with small tolerance)
        at_bottom = (new_scroll + 500) >= new_height
        
        # Try to find and click "Load More" or "Show More" buttons
        try:
            load_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "button[data-testid*='load'], button[data-testid*='more'], "
                "button:contains('Load'), button:contains('Show'), "
                ".load-more-button, [aria-label*='Load'], [aria-label*='More']")
            for btn in load_buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3)
                        print("  Clicked 'Load More' button")
                        break
                except:
                    continue
        except:
            pass
        
        # Check if page height changed (new content loaded)
        if new_height > last_height:
            print(f"  Scrolled to position {int(new_scroll)}/{int(new_height)} - New content loaded! (Total scrolls: {scroll_attempts + 1})")
            last_height = new_height
            consecutive_no_change = 0
        else:
            consecutive_no_change += 1
            if scroll_attempts % 10 == 0:  # Print every 10 scrolls
                print(f"  Scrolled to position {int(new_scroll)}/{int(new_height)} (Total scrolls: {scroll_attempts + 1})")
        
        # If we're at the bottom and no new content for several attempts, we're done
        if at_bottom and consecutive_no_change >= 5:
            print(f"  Reached bottom of page. No new content loading after {consecutive_no_change} attempts.")
            # Try one more aggressive scroll to trigger any lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            final_height = driver.execute_script("return document.body.scrollHeight")
            if final_height == new_height:
                print("  Confirmed: reached end of page")
                break
            else:
                last_height = final_height
                consecutive_no_change = 0
        
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
    
    # Final scroll to bottom to ensure everything is loaded
    print("  Performing final scroll to bottom...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)
    
    # Count final links
    final_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/r/']")
    unique_final_urls = set()
    for link in final_links:
        href = link.get_attribute('href')
        if href and '/r/' in href:
            clean_url = href.split('?')[0].split('#')[0]
            if '#reviews' not in clean_url and '#photos' not in clean_url:
                unique_final_urls.add(clean_url)
    print(f"  Final count: {len(unique_final_urls)} unique restaurant links found after scrolling")
    
    # Extract restaurant links
    print("Extracting restaurant links...")
    
    # Use JavaScript to extract all restaurant links from the page
    print("  Using JavaScript to extract links...")
    js_links = driver.execute_script("""
        var links = [];
        var seenUrls = new Set();
        
        // Method 1: Find all links with /r/ pattern
        var allLinks = document.querySelectorAll('a[href*="/r/"]');
        for (var i = 0; i < allLinks.length; i++) {
            var link = allLinks[i];
            var href = link.href || link.getAttribute('href');
            if (!href) continue;
            
            // Normalize URL
            if (href.startsWith('//')) href = 'https:' + href;
            if (href.startsWith('/')) href = 'https://www.opentable.com' + href;
            
            var cleanUrl = href.split('?')[0].split('#')[0];
            
            // Skip review/photos links and duplicates
            if (cleanUrl.includes('#reviews') || cleanUrl.includes('#photos') || !cleanUrl.includes('/r/') || seenUrls.has(cleanUrl)) {
                continue;
            }
            seenUrls.add(cleanUrl);
            
            // Try multiple methods to get restaurant name
            var name = '';
            
            // Method 1: Link text
            name = (link.textContent || link.innerText || '').trim();
            
            // Method 2: Look for restaurant name in parent/ancestor elements
            if (!name || name.length < 3) {
                var parent = link;
                for (var j = 0; j < 5 && parent; j++) {
                    parent = parent.parentElement;
                    if (parent) {
                        var parentText = (parent.textContent || '').trim();
                        // Look for text that looks like a restaurant name (first line, not too long)
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
            
            // Method 3: Extract from URL
            if (!name || name.length < 3) {
                var urlParts = cleanUrl.split('/r/');
                if (urlParts.length > 1) {
                    var slug = urlParts[1].split('?')[0].split('#')[0];
                    name = slug.replace(/-/g, ' ').replace(/\\b\\w/g, function(l) { return l.toUpperCase(); });
                }
            }
            
            // Clean up name - take first meaningful word/phrase
            if (name) {
                // Remove common prefixes/suffixes
                name = name.replace(/^(Icon|Promoted|Exceptional|Awesome)\\s*/i, '');
                // Take first line or first 50 chars
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
    
    # Add JavaScript-extracted links first
    for link_data in js_links:
        clean_url = link_data['url']
        if clean_url and '/r/' in clean_url and clean_url not in links_found:
            # Clean restaurant name - extract just the restaurant name
            name = link_data.get('name', '')
            if name:
                # Split by common separators
                import re
                # Remove rating numbers (4.8, 4.7, etc.)
                name = re.sub(r'\d+\.\d+', '', name)
                # Split by newlines and common words
                parts = re.split(r'[\n•]|Promoted|Exceptional|Awesome|Booked|Price:|Moderate|Expensive|Very Expensive', name)
                # Find the first meaningful part (usually the restaurant name)
                for part in parts:
                    part = part.strip()
                    # Skip if it's a number, rating word, or too short
                    if (part and len(part) > 2 
                        and not part.startswith('(') 
                        and not part.startswith('$')
                        and not part.isdigit()
                        and part.lower() not in ['promoted', 'exceptional', 'awesome', 'booked', 'price', 'moderate', 'expensive', 'very expensive', 'icon', 'seating options', 'times today', 'pts', 'pm', 'am']):
                        name = part
                        break
                
                # If still no good name, extract from URL
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
            print(f"    Found (JS): {name}")
    
    # Method 1: Find all links containing /r/ (OpenTable restaurant pattern)
    print("  Method 1: Searching for /r/ links...")
    try:
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            try:
                href = link.get_attribute('href')
                if href and '/r/' in href and 'opentable.com' in href:
                    # Clean the URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif not href.startswith('http'):
                        href = 'https://www.opentable.com' + href
                    
                    # Remove query parameters for unique ID
                    clean_url = href.split('?')[0]
                    
                    if clean_url not in links_found:
                        # Skip review links and other non-restaurant pages
                        if '#reviews' in clean_url or '#photos' in clean_url or '/r/' not in clean_url:
                            continue
                        
                        # Try to get restaurant name
                        restaurant_name = link.text.strip()
                        if not restaurant_name:
                            # Try parent element
                            try:
                                parent = link.find_element(By.XPATH, "./..")
                                restaurant_name = parent.text.strip()
                            except:
                                pass
                        
                        if not restaurant_name:
                            # Extract from URL
                            restaurant_name = clean_url.split('/r/')[-1].replace('-', ' ').title()
                        
                        # Clean restaurant name - take first line only
                        if restaurant_name:
                            # Split by newline and take first meaningful line
                            name_lines = [line.strip() for line in restaurant_name.split('\n') if line.strip()]
                            if name_lines:
                                # Skip lines that are just numbers, prices, or common words
                                filtered_lines = [line for line in name_lines 
                                                if not line.startswith('(') 
                                                and not line.startswith('$')
                                                and line.lower() not in ['promoted', 'exceptional', 'awesome', 'booked', 'price:', 'moderate', 'expensive', 'very expensive']
                                                and not line.isdigit()]
                                if filtered_lines:
                                    restaurant_name = filtered_lines[0]
                                else:
                                    restaurant_name = name_lines[0]
                        
                        restaurant_data = {
                            'name': restaurant_name,
                            'url': clean_url,
                            'opentable_id': clean_url.split('/r/')[-1].split('#')[0] if '/r/' in clean_url else None
                        }
                        links_found.add(clean_url)
                        restaurant_links.append(restaurant_data)
                        print(f"    Found: {restaurant_name}")
            except Exception as e:
                continue
    except Exception as e:
        print(f"  Error in Method 1: {e}")
    
    # Remove duplicates and filter out non-restaurant links
    seen_urls = set()
    unique_links = []
    for link in restaurant_links:
        url = link['url']
        # Skip review links, photo links, and other fragments
        if '#reviews' in url or '#photos' in url or '/r/' not in url:
            continue
        
        # Normalize URL (remove fragments and query params for deduplication)
        clean_url = url.split('#')[0].split('?')[0]
        
        # Only add if we haven't seen this restaurant ID before
        if clean_url not in seen_urls:
            seen_urls.add(clean_url)
            link['url'] = clean_url  # Update to clean URL
            # Clean up the name one more time
            if link['name']:
                # Remove extra whitespace and newlines
                link['name'] = ' '.join(link['name'].split())
            unique_links.append(link)
    
    restaurant_links = unique_links
    
    # Sort by name for easier reading
    restaurant_links.sort(key=lambda x: x['name'])
    
    print(f"\nPage {page_num} complete: Found {len(restaurant_links)} unique restaurant links")
    return restaurant_links


def scrape_opentable_links(url, output_file='opentable_restaurant_links.json', max_pages=12):
    """
    Scrape all restaurant links from OpenTable search results pages (with pagination)
    """
    print(f"Starting to scrape OpenTable pages (up to page {max_pages})")
    print(f"Initial URL: {url}")
    
    # Setup Chrome options
    options = Options()
    options.headless = True
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    
    all_restaurant_links = []
    all_seen_urls = set()
    
    try:
        print("Loading initial page...")
        driver.get(url)
        time.sleep(5)
        
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
        max_scrolls = 100  # Increased limit for very long pages
        no_change_count = 0
        consecutive_no_change = 0
        
        while scroll_attempts < max_scrolls:
            # Get current scroll position
            current_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
            page_height = driver.execute_script("return document.body.scrollHeight")
            
            # Scroll down slowly in small increments (simulating human behavior)
            scroll_increment = 300  # Scroll 300px at a time
            target_scroll = min(current_scroll + scroll_increment, page_height)
            
            driver.execute_script(f"window.scrollTo(0, {target_scroll});")
            time.sleep(1.5)  # Wait between scrolls
            
            # Check if we've reached the bottom
            new_height = driver.execute_script("return document.body.scrollHeight")
            new_scroll = driver.execute_script("return window.pageYOffset || document.documentElement.scrollTop")
            
            # Check if we're at the bottom (with small tolerance)
            at_bottom = (new_scroll + 500) >= new_height
            
            # Try to find and click "Load More" or "Show More" buttons
            try:
                load_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    "button[data-testid*='load'], button[data-testid*='more'], "
                    "button:contains('Load'), button:contains('Show'), "
                    ".load-more-button, [aria-label*='Load'], [aria-label*='More']")
                for btn in load_buttons:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(3)
                            print("  Clicked 'Load More' button")
                            break
                    except:
                        continue
            except:
                pass
            
            # Check if page height changed (new content loaded)
            if new_height > last_height:
                print(f"  Scrolled to position {int(new_scroll)}/{int(new_height)} - New content loaded! (Total scrolls: {scroll_attempts + 1})")
                last_height = new_height
                consecutive_no_change = 0
            else:
                consecutive_no_change += 1
                if scroll_attempts % 10 == 0:  # Print every 10 scrolls
                    print(f"  Scrolled to position {int(new_scroll)}/{int(new_height)} (Total scrolls: {scroll_attempts + 1})")
            
            # If we're at the bottom and no new content for several attempts, we're done
            if at_bottom and consecutive_no_change >= 5:
                print(f"  Reached bottom of page. No new content loading after {consecutive_no_change} attempts.")
                # Try one more aggressive scroll to trigger any lazy loading
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                final_height = driver.execute_script("return document.body.scrollHeight")
                if final_height == new_height:
                    print("  Confirmed: reached end of page")
                    break
                else:
                    last_height = final_height
                    consecutive_no_change = 0
            
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
        
        # Final scroll to bottom to ensure everything is loaded
        print("  Performing final scroll to bottom...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        
        # Count final links
        final_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/r/']")
        unique_final_urls = set()
        for link in final_links:
            href = link.get_attribute('href')
            if href and '/r/' in href:
                clean_url = href.split('?')[0].split('#')[0]
                if '#reviews' not in clean_url and '#photos' not in clean_url:
                    unique_final_urls.add(clean_url)
        print(f"  Final count: {len(unique_final_urls)} unique restaurant links found after scrolling")
        
        # Find all restaurant links
        print("Extracting restaurant links...")
        
        # Use JavaScript to extract all restaurant links from the page
        print("  Using JavaScript to extract links...")
        js_links = driver.execute_script("""
            var links = [];
            var seenUrls = new Set();
            
            // Method 1: Find all links with /r/ pattern
            var allLinks = document.querySelectorAll('a[href*="/r/"]');
            for (var i = 0; i < allLinks.length; i++) {
                var link = allLinks[i];
                var href = link.href || link.getAttribute('href');
                if (!href) continue;
                
                // Normalize URL
                if (href.startsWith('//')) href = 'https:' + href;
                if (href.startsWith('/')) href = 'https://www.opentable.com' + href;
                
                var cleanUrl = href.split('?')[0].split('#')[0];
                
                // Skip review/photos links and duplicates
                if (cleanUrl.includes('#reviews') || cleanUrl.includes('#photos') || !cleanUrl.includes('/r/') || seenUrls.has(cleanUrl)) {
                    continue;
                }
                seenUrls.add(cleanUrl);
                
                // Try multiple methods to get restaurant name
                var name = '';
                
                // Method 1: Link text
                name = (link.textContent || link.innerText || '').trim();
                
                // Method 2: Look for restaurant name in parent/ancestor elements
                if (!name || name.length < 3) {
                    var parent = link;
                    for (var j = 0; j < 5 && parent; j++) {
                        parent = parent.parentElement;
                        if (parent) {
                            var parentText = (parent.textContent || '').trim();
                            // Look for text that looks like a restaurant name (first line, not too long)
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
                
                // Method 3: Extract from URL
                if (!name || name.length < 3) {
                    var urlParts = cleanUrl.split('/r/');
                    if (urlParts.length > 1) {
                        var slug = urlParts[1].split('?')[0].split('#')[0];
                        name = slug.replace(/-/g, ' ').replace(/\\b\\w/g, function(l) { return l.toUpperCase(); });
                    }
                }
                
                // Clean up name - take first meaningful word/phrase
                if (name) {
                    // Remove common prefixes/suffixes
                    name = name.replace(/^(Icon|Promoted|Exceptional|Awesome)\\s*/i, '');
                    // Take first line or first 50 chars
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
        
        links_found = set()  # Use set to avoid duplicates
        
        # Add JavaScript-extracted links first
        for link_data in js_links:
            clean_url = link_data['url']
            if clean_url and '/r/' in clean_url and clean_url not in links_found:
                # Clean restaurant name - extract just the restaurant name
                name = link_data.get('name', '')
                if name:
                    # Split by common separators
                    import re
                    # Remove rating numbers (4.8, 4.7, etc.)
                    name = re.sub(r'\d+\.\d+', '', name)
                    # Split by newlines and common words
                    parts = re.split(r'[\n•]|Promoted|Exceptional|Awesome|Booked|Price:|Moderate|Expensive|Very Expensive', name)
                    # Find the first meaningful part (usually the restaurant name)
                    for part in parts:
                        part = part.strip()
                        # Skip if it's a number, rating word, or too short
                        if (part and len(part) > 2 
                            and not part.startswith('(') 
                            and not part.startswith('$')
                            and not part.isdigit()
                            and part.lower() not in ['promoted', 'exceptional', 'awesome', 'booked', 'price', 'moderate', 'expensive', 'very expensive', 'icon', 'seating options', 'times today', 'pts', 'pm', 'am']):
                            name = part
                            break
                    
                    # If still no good name, extract from URL
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
                print(f"    Found (JS): {name}")
        
        # Method 1: Find all links containing /r/ (OpenTable restaurant pattern)
        print("  Method 1: Searching for /r/ links...")
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    if href and '/r/' in href and 'opentable.com' in href:
                        # Clean the URL
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif not href.startswith('http'):
                            href = 'https://www.opentable.com' + href
                        
                        # Remove query parameters for unique ID
                        clean_url = href.split('?')[0]
                        
                        if clean_url not in links_found:
                            # Try to get restaurant name
                            restaurant_name = link.text.strip()
                            if not restaurant_name:
                                # Try parent element
                                try:
                                    parent = link.find_element(By.XPATH, "./..")
                                    restaurant_name = parent.text.strip()
                                except:
                                    pass
                            
                            if not restaurant_name:
                                # Extract from URL
                                restaurant_name = clean_url.split('/r/')[-1].replace('-', ' ').title()
                            
                            # Skip review links and other non-restaurant pages
                            if '#reviews' in clean_url or '#photos' in clean_url or '/r/' not in clean_url:
                                continue
                            
                            # Clean restaurant name - take first line only
                            if restaurant_name:
                                # Split by newline and take first meaningful line
                                name_lines = [line.strip() for line in restaurant_name.split('\n') if line.strip()]
                                if name_lines:
                                    # Skip lines that are just numbers, prices, or common words
                                    filtered_lines = [line for line in name_lines 
                                                    if not line.startswith('(') 
                                                    and not line.startswith('$')
                                                    and line.lower() not in ['promoted', 'exceptional', 'awesome', 'booked', 'price:', 'moderate', 'expensive', 'very expensive']
                                                    and not line.isdigit()]
                                    if filtered_lines:
                                        restaurant_name = filtered_lines[0]
                                    else:
                                        restaurant_name = name_lines[0]
                            
                            restaurant_data = {
                                'name': restaurant_name,
                                'url': clean_url,
                                'opentable_id': clean_url.split('/r/')[-1].split('#')[0] if '/r/' in clean_url else None
                            }
                            links_found.add(clean_url)
                            restaurant_links.append(restaurant_data)
                            print(f"    Found: {restaurant_name}")
                except Exception as e:
                    continue
        except Exception as e:
            print(f"  Error in Method 1: {e}")
        
        # Method 2: Search by various CSS selectors
        print("  Method 2: Searching with CSS selectors...")
        selectors = [
            "a[href*='/r/']",
            "[data-testid*='restaurant'] a",
            ".restaurant-card a",
            "[class*='restaurant'] a",
            "[class*='Restaurant'] a"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        href = elem.get_attribute('href')
                        if href and '/r/' in href:
                            if href.startswith('//'):
                                href = 'https:' + href
                            elif not href.startswith('http'):
                                href = 'https://www.opentable.com' + href
                            
                            clean_url = href.split('?')[0]
                            if clean_url not in links_found:
                                restaurant_name = elem.text.strip() or clean_url.split('/r/')[-1].replace('-', ' ').title()
                                restaurant_data = {
                                    'name': restaurant_name,
                                    'url': clean_url,
                                    'opentable_id': clean_url.split('/r/')[-1] if '/r/' in clean_url else None
                                }
                                links_found.add(clean_url)
                                restaurant_links.append(restaurant_data)
                    except:
                        continue
            except:
                continue
        
        # Method 3: XPath search
        print("  Method 3: Searching with XPath...")
        try:
            xpath_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/r/')]")
            for link in xpath_links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        if href.startswith('//'):
                            href = 'https:' + href
                        elif not href.startswith('http'):
                            href = 'https://www.opentable.com' + href
                        
                        clean_url = href.split('?')[0]
                        if clean_url not in links_found and '/r/' in clean_url:
                            restaurant_name = link.text.strip() or clean_url.split('/r/')[-1].replace('-', ' ').title()
                            restaurant_data = {
                                'name': restaurant_name,
                                'url': clean_url,
                                'opentable_id': clean_url.split('/r/')[-1] if '/r/' in clean_url else None
                            }
                            links_found.add(clean_url)
                            restaurant_links.append(restaurant_data)
                except:
                    continue
        except Exception as e:
            print(f"  Error in Method 3: {e}")
        
        # Remove duplicates and filter out non-restaurant links
        seen_urls = set()
        unique_links = []
        for link in restaurant_links:
            url = link['url']
            # Skip review links, photo links, and other fragments
            if '#reviews' in url or '#photos' in url or '/r/' not in url:
                continue
            
            # Normalize URL (remove fragments and query params for deduplication)
            clean_url = url.split('#')[0].split('?')[0]
            
            # Only add if we haven't seen this restaurant ID before
            if clean_url not in seen_urls:
                seen_urls.add(clean_url)
                link['url'] = clean_url  # Update to clean URL
                # Clean up the name one more time
                if link['name']:
                    # Remove extra whitespace and newlines
                    link['name'] = ' '.join(link['name'].split())
                unique_links.append(link)
        
        restaurant_links = unique_links
        
        # Sort by name for easier reading
        restaurant_links.sort(key=lambda x: x['name'])
        
        print(f"\nTotal unique restaurant links found: {len(restaurant_links)}")
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(restaurant_links, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(restaurant_links)} restaurant links to {output_file}")
        
        return restaurant_links
        
    except Exception as e:
        print(f"Error scraping page: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        driver.quit()


if __name__ == "__main__":
    url = "https://www.opentable.com/s?dateTime=2025-12-03T19%3A00%3A00&covers=2&latitude=40.712778&longitude=-74.006111&term=New%20York&shouldUseLatLongSearch=true&originCorrelationId=9bb22629-d46b-4b64-b347-6aa250626638&corrid=15f395fa-50b1-425e-aea8-e1a7faa1f9a9&metroId=8&originalTerm=New%20York&queryUnderstandingType=location&showMap=true&sortBy=web_conversion"
    
    links = scrape_opentable_links(url, 'opentable_restaurant_links.json', max_pages=12)
    print(f"\nScraping complete! Found {len(links)} unique restaurant links across all pages.")

