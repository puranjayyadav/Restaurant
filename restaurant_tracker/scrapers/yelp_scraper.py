"""
Script to scrape detailed information from Yelp restaurant pages
"""

from playwright.sync_api import sync_playwright
import json
import time
import os
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse
from pathlib import Path

def find_brave_path():
    """Find Brave browser executable path"""
    possible_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def download_image_with_page(page, image_url: str, save_path: str) -> bool:
    """Download an image using page's request context (with proper headers/cookies from Yelp session)"""
    try:
        # Use the page's request context which has all cookies and headers from Yelp
        response = page.request.get(image_url)
        if response.status == 200:
            with open(save_path, 'wb') as f:
                f.write(response.body())
            return True
        else:
            print(f"      ⚠️  Failed to download: Status {response.status}")
            return False
    except Exception as e:
        print(f"      ⚠️  Error downloading: {e}")
        return False

def download_images(page, image_urls: List[str], restaurant_name: str, base_dir: str = "restaurant_images") -> List[str]:
    """Download images and return local file paths"""
    # Create directory for images
    images_dir = Path(base_dir)
    images_dir.mkdir(exist_ok=True)
    
    # Sanitize restaurant name for filename
    safe_name = "".join(c for c in restaurant_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_name = safe_name.replace(' ', '_')[:50]  # Limit length
    
    local_paths = []
    
    for i, img_url in enumerate(image_urls[:5], 1):  # Download first 5 images
        try:
            # Get file extension from URL
            parsed = urlparse(img_url)
            ext = os.path.splitext(parsed.path)[1] or '.jpg'
            if '?' in ext:
                ext = ext.split('?')[0]
            
            # Create filename
            filename = f"{i:02d}_{safe_name}{ext}"
            filepath = images_dir / filename
            
            # Download using page's request context (has Yelp cookies/headers)
            if download_image_with_page(page, img_url, str(filepath)):
                local_paths.append(str(filepath))
                print(f"      ✅ Downloaded: {filename}")
            else:
                print(f"      ❌ Failed to download image {i}")
        except Exception as e:
            print(f"      ⚠️  Error processing image {i}: {e}")
    
    return local_paths

def scrape_restaurant_detail(page, url: str, download_images_local: bool = True) -> Dict:
    """Scrape detailed information from a Yelp restaurant page"""
    restaurant = {
        "url": url,
        "name": None,
        "rating": None,
        "review_count": None,
        "price_range": None,
        "cuisine": None,
        "address": None,
        "phone": None,
        "website": None,
        "hours": None,
        "description": None,
        "images": [],
        "reviews": [],
        "popular_dishes": [],
        "menu_link": None,
        "amenities": [],
        "location": None,
    }
    
    try:
        # Navigate to the page with retry logic
        # Use 'load' instead of 'networkidle' - it's more reliable for pages with continuous network activity
        max_retries = 2
        page_loaded = False
        
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    # First try: use 'load' which waits for page load event (more reliable than networkidle)
                    page.goto(url, wait_until="load", timeout=45000)
                else:
                    # Fallback: try domcontentloaded (faster, less strict)
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page_loaded = True
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    ⚠️  Load attempt {attempt + 1} failed, retrying with different strategy...")
                    time.sleep(1)
                else:
                    # Last attempt failed - but continue anyway, page might have loaded partially
                    print(f"    ⚠️  Page load timeout, but continuing with partial page...")
                    page_loaded = True  # Continue anyway
                    break
        
        # Wait for dynamic content to load - increased wait time significantly
        print("    ⏳ Waiting for page to fully load...")
        time.sleep(8)  # Increased from 5 to 8 seconds
        
        # Try to wait for key elements to appear
        try:
            # Wait for name element to appear (with timeout)
            print("    ⏳ Waiting for h1 element...")
            page.wait_for_selector('h1', timeout=15000)
            print("    ✅ h1 element found")
        except Exception as e:
            print(f"    ⚠️  h1 wait timeout: {e}")
            pass  # Continue even if timeout
        
        # Additional wait for JavaScript to render
        time.sleep(3)
        
        # Check if we're blocked or see a captcha
        try:
            page_text = page.inner_text('body')
            if 'captcha' in page_text.lower() or 'verify' in page_text.lower() or 'challenge' in page_text.lower():
                print("    ⚠️  WARNING: Possible captcha or verification page detected!")
            if len(page_text) < 1000:
                print(f"    ⚠️  WARNING: Page content seems very short ({len(page_text)} chars), might be blocked")
        except:
            pass
        
        print("    ✅ Page load complete, starting extraction...")
        
        # Extract name - use JavaScript first for better reliability
        try:
            # Primary: Use JavaScript to extract name (more reliable)
            name_data = page.evaluate('''
                () => {
                    // Try specific Yelp selectors first
                    const selectors = [
                        'h1.y-css-olzveb',
                        'h1[class*="heading"]',
                        'h1',
                        '[data-testid="business-name"]',
                        'h1.biz-page-title',
                        '[class*="business-name"]',
                        '[class*="heading"]'
                    ];
                    
                    for (const selector of selectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            const text = elem.innerText?.trim() || elem.textContent?.trim();
                            if (text && text.length > 0 && text.length < 100) {
                                return text;
                            }
                        }
                    }
                    
                    // Fallback to page title
                    const title = document.title;
                    if (title && title.includes(' - ')) {
                        return title.split(' - ')[0].trim();
                    }
                    
                    return null;
                }
            ''')
            
            if name_data:
                restaurant["name"] = name_data
                print(f"    ✅ Found name: {restaurant['name']}")
            else:
                # Fallback: Try Playwright selectors
                name_selectors = [
                    'h1.y-css-olzveb',
                    'h1[class*="heading"]',
                    'h1',
                    '[data-testid="business-name"]',
                    'h1.biz-page-title',
                    '[class*="business-name"]',
                ]
                for selector in name_selectors:
                    name_elem = page.query_selector(selector)
                    if name_elem:
                        text = name_elem.inner_text().strip()
                        if text and len(text) < 100:
                            restaurant["name"] = text
                            print(f"    ✅ Found name: {restaurant['name']}")
                            break
        except Exception as e:
            print(f"    ⚠️  Error extracting name: {e}")
            pass
        
        # Extract rating - use JavaScript for better reliability
        try:
            rating_data = page.evaluate('''
                () => {
                    // Try aria-label first (most reliable)
                    const ratingElems = document.querySelectorAll('[aria-label*="star rating"], [aria-label*="rating"]');
                    for (const elem of ratingElems) {
                        const ariaLabel = elem.getAttribute('aria-label') || '';
                        const match = ariaLabel.match(/(\\d+\\.?\\d*)\\s*star/i);
                        if (match) {
                            return parseFloat(match[1]);
                        }
                    }
                    
                    // Try text content with rating pattern
                    const allText = document.body.innerText;
                    const ratingMatch = allText.match(/(\\d+\\.?\\d*)\\s*star/i);
                    if (ratingMatch) {
                        return parseFloat(ratingMatch[1]);
                    }
                    
                    // Try class-based selectors
                    const classElems = document.querySelectorAll('[class*="rating"], [class*="star"]');
                    for (const elem of classElems) {
                        const text = elem.innerText || elem.getAttribute('aria-label') || '';
                        const match = text.match(/(\\d+\\.?\\d*)\\s*star/i);
                        if (match) {
                            return parseFloat(match[1]);
                        }
                    }
                    
                    return null;
                }
            ''')
            
            if rating_data:
                restaurant["rating"] = float(rating_data)
                print(f"    ⭐ Rating: {restaurant['rating']}")
            else:
                # Fallback: Try Playwright selectors
                rating_selectors = [
                    '[aria-label*="star rating"]',
                    '[aria-label*="rating"]',
                    '[class*="rating"]',
                    '[data-testid="rating"]',
                    'span[class*="star"]',
                ]
                for selector in rating_selectors:
                    rating_elems = page.query_selector_all(selector)
                    for rating_elem in rating_elems:
                        rating_text = rating_elem.get_attribute('aria-label') or rating_elem.inner_text()
                        import re
                        rating_match = re.search(r'(\d+\.?\d*)\s*star', rating_text, re.IGNORECASE)
                        if rating_match:
                            restaurant["rating"] = float(rating_match.group(1))
                            print(f"    ⭐ Rating: {restaurant['rating']}")
                            break
                    if restaurant["rating"]:
                        break
        except Exception as e:
            print(f"    ⚠️  Error extracting rating: {e}")
            pass
        
        # Extract review count - use JavaScript for better reliability
        try:
            review_count_data = page.evaluate('''
                () => {
                    // Try to find review count text
                    const allText = document.body.innerText;
                    
                    // Pattern: "123 reviews" or "1,234 reviews"
                    const reviewMatch = allText.match(/(\\d{1,3}(?:,\\d{3})*)\\s*review/i);
                    if (reviewMatch) {
                        return parseInt(reviewMatch[1].replace(/,/g, ''));
                    }
                    
                    // Try specific selectors
                    const selectors = [
                        '[class*="review-count"]',
                        '[data-testid="review-count"]',
                        '[class*="review"]'
                    ];
                    
                    for (const selector of selectors) {
                        const elems = document.querySelectorAll(selector);
                        for (const elem of elems) {
                            const text = elem.innerText || '';
                            const match = text.match(/(\\d{1,3}(?:,\\d{3})*)/);
                            if (match && text.toLowerCase().includes('review')) {
                                return parseInt(match[1].replace(/,/g, ''));
                            }
                        }
                    }
                    
                    // Also try to find spans with review text
                    const allSpans = document.querySelectorAll('span');
                    for (const span of allSpans) {
                        const text = span.innerText || '';
                        if (text.toLowerCase().includes('review') && /\\d/.test(text)) {
                            const match = text.match(/(\\d{1,3}(?:,\\d{3})*)/);
                            if (match) {
                                return parseInt(match[1].replace(/,/g, ''));
                            }
                        }
                    }
                    
                    return null;
                }
            ''')
            
            if review_count_data:
                restaurant["review_count"] = int(review_count_data)
                print(f"    📊 Reviews: {restaurant['review_count']}")
            else:
                # Fallback: Try Playwright selectors
                review_count_selectors = [
                    '[class*="review-count"]',
                    'span:has-text("reviews")',
                    '[data-testid="review-count"]',
                ]
                for selector in review_count_selectors:
                    review_elem = page.query_selector(selector)
                    if review_elem:
                        review_text = review_elem.inner_text()
                        import re
                        review_match = re.search(r'(\d{1,3}(?:,\d{3})*)', review_text.replace(',', ''))
                        if review_match:
                            restaurant["review_count"] = int(review_match.group(1).replace(',', ''))
                            print(f"    📊 Reviews: {restaurant['review_count']}")
                            break
        except Exception as e:
            print(f"    ⚠️  Error extracting review count: {e}")
            pass
        
        # Extract address - use JavaScript for better reliability
        try:
            address_data = page.evaluate('''
                () => {
                    // Try address tag first
                    const addrEl = document.querySelector('address');
                    if (addrEl) {
                        const text = addrEl.innerText?.trim();
                        if (text && text.length > 5) {
                            return text;
                        }
                    }
                    
                    // Try class-based selectors
                    const selectors = [
                        '[class*="address"]',
                        '[data-testid="address"]',
                        '[class*="location"]',
                        'p[class*="address"]'
                    ];
                    
                    for (const selector of selectors) {
                        const elems = document.querySelectorAll(selector);
                        for (const elem of elems) {
                            const text = elem.innerText?.trim();
                            // Check if it looks like an address (has comma, city, or state)
                            if (text && (text.includes(',') || text.includes('New York') || text.includes('NY') || /\\d+/.test(text))) {
                                if (text.length > 5 && text.length < 200) {
                                    return text;
                                }
                            }
                        }
                    }
                    
                    // Fallback: Search in all text for address pattern
                    const allText = document.body.innerText;
                    const addrMatch = allText.match(/\\d+[\\s\\S]{0,100}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr)[\\s\\S]{0,100}(?:New York|NY|Brooklyn|Queens|Bronx|Manhattan)[\\s\\S]{0,50}/i);
                    if (addrMatch) {
                        return addrMatch[0].trim();
                    }
                    
                    return null;
                }
            ''')
            
            if address_data:
                restaurant["address"] = address_data
                print(f"    📍 Address: {restaurant['address'][:50]}...")
            else:
                # Fallback: Try Playwright selectors
                address_selectors = [
                    'address',
                    '[class*="address"]',
                    '[data-testid="address"]',
                    'p:has-text("New York")',
                    'p:has-text("NY")',
                    '[class*="location"]',
                ]
                for selector in address_selectors:
                    addr_elems = page.query_selector_all(selector)
                    for addr_elem in addr_elems:
                        addr_text = addr_elem.inner_text().strip()
                        if addr_text and (',' in addr_text or 'New York' in addr_text or 'NY' in addr_text):
                            restaurant["address"] = addr_text
                            print(f"    📍 Address: {restaurant['address'][:50]}...")
                            break
                    if restaurant["address"]:
                        break
        except Exception as e:
            print(f"    ⚠️  Error extracting address: {e}")
            pass
        
        # Extract phone
        try:
            phone_selectors = [
                'p.y-css-qn4gww[data-font-weight="semibold"]',  # Specific Yelp phone selector
                'p.y-css-qn4gww',  # Fallback to just the class
                'p[data-font-weight="semibold"]:has-text("(")',  # Any semibold paragraph with phone format
                'a[href^="tel:"]',
                '[class*="phone"]',
                '[data-testid="phone"]',
                'p:has-text("(")',
                '[aria-label*="phone"]',
            ]
            for selector in phone_selectors:
                phone_elems = page.query_selector_all(selector)
                for phone_elem in phone_elems:
                    phone_text = phone_elem.inner_text() or phone_elem.get_attribute('href', '').replace('tel:', '')
                    if phone_text:
                        # Check if it looks like a phone number (US format: (XXX) XXX-XXXX or similar)
                        import re
                        phone_clean = re.sub(r'[^\d()\-+\s]', '', phone_text)
                        digit_count = len([c for c in phone_clean if c.isdigit()])
                        
                        # Match common phone patterns: (212) 334-9020, 212-334-9020, etc.
                        phone_pattern = re.search(r'\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}', phone_text)
                        
                        if phone_pattern or digit_count >= 10:  # At least 10 digits or matches pattern
                            restaurant["phone"] = phone_text.strip()
                            print(f"    📞 Found phone: {restaurant['phone']}")
                            break
                if restaurant["phone"]:
                    break
        except:
            pass
        
        # Extract website
        try:
            website_elem = page.query_selector('a[href*="biz_redir"]')
            if website_elem:
                restaurant["website"] = website_elem.get_attribute('href')
        except:
            pass
        
        # Extract price range
        try:
            price_elem = page.query_selector('span:has-text("$")')
            if price_elem:
                restaurant["price_range"] = price_elem.inner_text().strip()
        except:
            pass
        
        # Extract cuisine/categories
        try:
            cuisine_elems = page.query_selector_all('[class*="category"], [class*="cuisine"], a[href*="/c/"]')
            cuisines = []
            for elem in cuisine_elems[:5]:  # Limit to first 5
                text = elem.inner_text().strip()
                if text and len(text) < 50:  # Reasonable category length
                    cuisines.append(text)
            if cuisines:
                restaurant["cuisine"] = ", ".join(cuisines)
        except:
            pass
        
        # Extract hours
        try:
            hours_elem = page.query_selector('[class*="hours"], [data-testid="hours"]')
            if hours_elem:
                restaurant["hours"] = hours_elem.inner_text().strip()
        except:
            pass
        
        # Extract description/about
        try:
            desc_selectors = [
                '[class*="description"]',
                '[class*="about"]',
                'p[class*="text"]',
            ]
            for selector in desc_selectors:
                desc_elem = page.query_selector(selector)
                if desc_elem:
                    text = desc_elem.inner_text().strip()
                    if len(text) > 20:  # Meaningful description
                        restaurant["description"] = text
                        break
        except:
            pass
        
        # Extract images - click photos link and get from photos tab
        try:
            # Try to click "See all X photos" link
            photos_link = page.query_selector('a[href*="/biz_photos"]')
            if photos_link:
                print("    📷 Clicking photos link...")
                photos_link.click()
                time.sleep(3)  # Wait for photos page to load
                
                # Try to click on the Food tab
                # The tabs are: All, Food, Inside, Menu, Drink, Outside, Videos
                # Food is the 2nd tab (index 1)
                try:
                    # Use JavaScript to find and click Food tab more reliably
                    food_tab_clicked = page.evaluate('''
                        () => {
                            const tabs = document.querySelectorAll('[role="tab"]');
                            for (let i = 0; i < tabs.length; i++) {
                                const tab = tabs[i];
                                const text = tab.innerText || tab.textContent || '';
                                if (text.includes('Food') && !text.includes('All')) {
                                    tab.click();
                                    return true;
                                }
                            }
                            // Fallback: click 2nd tab (Food is usually 2nd)
                            if (tabs.length >= 2) {
                                tabs[1].click();
                                return true;
                            }
                            return false;
                        }
                    ''')
                    
                    if food_tab_clicked:
                        print("    🍽️  Clicked Food tab...")
                        time.sleep(3)  # Wait for images to load
                    else:
                        print("    ⚠️  Food tab not found")
                except Exception as e:
                    print(f"    ⚠️  Could not click Food tab: {e}")
                
                # Now extract images from the photos page (Food tab)
                # Look for images in the photo grid - try multiple selectors
                img_selectors = [
                    'img.y-css-3xip89',  # Specific class from user's HTML
                    'img[src*="s3-media"]',
                    'img[src*="yelpcdn"]',
                    'img[data-testid="thumbnail"]',
                    '[data-testid="thumbnail"] img',
                ]
                
                images = []
                seen_srcs = set()
                
                for selector in img_selectors:
                    img_elems = page.query_selector_all(selector)
                    if img_elems:
                        for img in img_elems:
                            src = img.get_attribute('src') or img.get_attribute('data-src')
                            if src:
                                # Get full resolution image URL (remove size parameters)
                                # Yelp images have format like: https://s3-media0.fl.yelpcdn.com/bphoto/.../348s.jpg
                                # We want the full size, so remove the size suffix
                                if '/348s.jpg' in src:
                                    src = src.replace('/348s.jpg', '.jpg')
                                elif '/258s.jpg' in src:
                                    src = src.replace('/258s.jpg', '.jpg')
                                
                                # Clean up the URL
                                if '?' in src:
                                    src = src.split('?')[0]
                                
                                if src and 'yelp' in src.lower() and 'bphoto' in src and src not in seen_srcs:
                                    seen_srcs.add(src)
                                    images.append(src)
                                    if len(images) >= 5:  # Get first 5 photos
                                        break
                    
                    if len(images) >= 5:
                        break
                
                # Download images if requested
                if download_images_local and images:
                    print(f"    📥 Downloading {len(images)} images...")
                    restaurant_name = restaurant.get("name") or "restaurant"
                    local_image_paths = download_images(page, images, restaurant_name)
                    restaurant["images"] = local_image_paths  # Store local paths instead of URLs
                    restaurant["image_urls"] = images  # Keep original URLs as backup
                else:
                    restaurant["images"] = images
                
                print(f"    ✅ Found {len(images)} photos from Food tab")
            else:
                # Fallback: try to get images from main page
                img_elems = page.query_selector_all('img[src*="s3-media"], img[class*="photo"]')
                images = []
                for img in img_elems[:5]:  # Limit to first 5 images
                    src = img.get_attribute('src') or img.get_attribute('data-src')
                    if src and 'yelp' in src.lower():
                        images.append(src)
                restaurant["images"] = list(set(images))  # Remove duplicates
        except Exception as e:
            print(f"    ⚠️  Error extracting images: {e}")
            restaurant["images"] = []
        
        # Extract menu link
        try:
            menu_selectors = [
                'a[href*="menu"]',
                'a[href*="/menu"]',
                'a:has-text("Menu")',
                '[class*="menu"][href]',
            ]
            for selector in menu_selectors:
                menu_elem = page.query_selector(selector)
                if menu_elem:
                    href = menu_elem.get_attribute('href')
                    if href:
                        # Handle relative URLs
                        if href.startswith('/'):
                            restaurant["menu_link"] = f"https://www.yelp.com{href}"
                        elif href.startswith('http'):
                            restaurant["menu_link"] = href
                        else:
                            restaurant["menu_link"] = f"https://www.yelp.com/{href}"
                        print(f"    📋 Found menu link: {restaurant['menu_link']}")
                        break
        except Exception as e:
            print(f"    ⚠️  Error extracting menu link: {e}")
        
        # Extract popular dishes (name and 5 photos per dish)
        try:
            # Look for popular dishes section
            # Common selectors for popular dishes on Yelp
            dish_selectors = [
                '[class*="dish"]',
                '[class*="popular"]',
                '[data-testid*="dish"]',
            ]
            
            popular_dishes = []
            
            # Try to find dish containers
            for selector in dish_selectors:
                dish_containers = page.query_selector_all(selector)
                if dish_containers:
                    for container in dish_containers[:5]:  # Limit to first 5 dishes
                        try:
                            # Extract dish name
                            name_elem = container.query_selector('h3, h4, p[class*="name"], span[class*="name"]')
                            dish_name = name_elem.inner_text().strip() if name_elem else None
                            
                            if dish_name:
                                # Extract images for this dish
                                dish_images = []
                                img_elems = container.query_selector_all('img')
                                for img in img_elems[:5]:  # First 5 images per dish
                                    src = img.get_attribute('src') or img.get_attribute('data-src')
                                    if src and 'yelp' in src.lower():
                                        # Get full resolution
                                        if '/348s.jpg' in src:
                                            src = src.replace('/348s.jpg', '.jpg')
                                        elif '/258s.jpg' in src:
                                            src = src.replace('/258s.jpg', '.jpg')
                                        dish_images.append(src)
                                
                                popular_dishes.append({
                                    "name": dish_name,
                                    "images": dish_images[:5]  # Limit to 5 images
                                })
                        except:
                            continue
                    
                    if popular_dishes:
                        break
            
            # Alternative: Use JavaScript to extract popular dishes
            if not popular_dishes:
                try:
                    dish_data = page.evaluate('''
                        () => {
                            const dishes = [];
                            // Look for dish-related elements
                            const containers = document.querySelectorAll('[class*="dish"], [class*="popular-dish"]');
                            containers.forEach(container => {
                                const nameEl = container.querySelector('h3, h4, p, span');
                                if (nameEl) {
                                    const name = nameEl.innerText.trim();
                                    if (name && name.length > 2 && name.length < 100) {
                                        const imgs = container.querySelectorAll('img');
                                        const images = [];
                                        imgs.forEach(img => {
                                            if (img.src && img.src.includes('yelp')) {
                                                let src = img.src;
                                                if (src.includes('/348s.jpg')) {
                                                    src = src.replace('/348s.jpg', '.jpg');
                                                } else if (src.includes('/258s.jpg')) {
                                                    src = src.replace('/258s.jpg', '.jpg');
                                                }
                                                images.push(src);
                                            }
                                        });
                                        if (name) {
                                            dishes.push({
                                                name: name,
                                                images: images.slice(0, 5)
                                            });
                                        }
                                    }
                                }
                            });
                            return dishes.slice(0, 5); // Return first 5 dishes
                        }
                    ''')
                    if dish_data:
                        popular_dishes = dish_data
                except:
                    pass
            
            restaurant["popular_dishes"] = popular_dishes
            if popular_dishes:
                print(f"    🍽️  Found {len(popular_dishes)} popular dishes")
        except Exception as e:
            print(f"    ⚠️  Error extracting popular dishes: {e}")
            restaurant["popular_dishes"] = []
        
        # Extract reviews (first 5)
        try:
            # Try multiple selectors for reviews
            review_selectors = [
                'li.y-css-1sqelp2 div.comment__09f24__D0cxf p.raw__09f24__T4Ezm',  # From user's HTML
                '[class*="review"] p[class*="comment"]',
                '[class*="review-text"]',
                '[data-testid="review"] p',
                'p[class*="review"]',
            ]
            
            reviews = []
            for selector in review_selectors:
                review_elems = page.query_selector_all(selector)
                if review_elems:
                    for review_elem in review_elems[:5]:  # First 5 reviews
                        try:
                            review_text = review_elem.inner_text().strip()
                            if len(review_text) > 10:
                                reviews.append(review_text[:500])  # Limit length
                                if len(reviews) >= 5:
                                    break
                        except:
                            continue
                
                if len(reviews) >= 5:
                    break
            
            # Fallback: Use JavaScript to extract reviews
            if not reviews:
                try:
                    review_data = page.evaluate('''
                        () => {
                            const reviews = [];
                            // Look for review text elements
                            const reviewElems = document.querySelectorAll('p[class*="comment"], p[class*="review"], [class*="review-text"]');
                            reviewElems.forEach(elem => {
                                const text = elem.innerText.trim();
                                if (text && text.length > 10 && text.length < 1000) {
                                    reviews.push(text.substring(0, 500));
                                }
                            });
                            return reviews.slice(0, 5);
                        }
                    ''')
                    if review_data:
                        reviews = review_data
                except:
                    pass
            
            restaurant["reviews"] = reviews
            if reviews:
                print(f"    ⭐ Found {len(reviews)} reviews")
        except Exception as e:
            print(f"    ⚠️  Error extracting reviews: {e}")
            restaurant["reviews"] = []
        
        # Use JavaScript to extract more data as fallback
        try:
            page_data = page.evaluate('''
                () => {
                    const data = {};
                    
                    // Get name from title or h1
                    if (!data.name) {
                        const title = document.title;
                        if (title && title.includes(' - ')) {
                            data.name = title.split(' - ')[0].trim();
                        }
                    }
                    if (!data.name) {
                        const nameEl = document.querySelector('h1');
                        if (nameEl) data.name = nameEl.innerText.trim();
                    }
                    
                    // Get address
                    const addrEl = document.querySelector('address');
                    if (addrEl) {
                        data.address = addrEl.innerText.trim();
                    } else {
                        // Try to find address in text
                        const allText = document.body.innerText;
                        const addrMatch = allText.match(/\\d+[\\s\\S]{0,100}New York[\\s\\S]{0,50}/);
                        if (addrMatch) data.address = addrMatch[0].trim();
                    }
                    
                    // Get phone - try multiple selectors
                    let phoneEl = document.querySelector('p.y-css-qn4gww[data-font-weight="semibold"]');
                    if (!phoneEl) {
                        phoneEl = document.querySelector('p.y-css-qn4gww');
                    }
                    if (!phoneEl) {
                        phoneEl = document.querySelector('a[href^="tel:"]');
                    }
                    if (phoneEl) {
                        const phoneText = phoneEl.innerText?.trim() || phoneEl.getAttribute('href')?.replace('tel:', '') || '';
                        // Check if it looks like a phone number
                        if (phoneText.match(/\\(?\\d{3}\\)?[\\s\\-]?\\d{3}[\\s\\-]?\\d{4}/) || phoneText.replace(/[^\\d]/g, '').length >= 10) {
                            data.phone = phoneText;
                        }
                    }
                    
                    // Get rating from aria-label
                    const ratingEl = document.querySelector('[aria-label*="star rating"]');
                    if (ratingEl) {
                        const ariaLabel = ratingEl.getAttribute('aria-label') || '';
                        const match = ariaLabel.match(/(\\d+\\.?\\d*)\\s*star/i);
                        if (match) data.rating = parseFloat(match[1]);
                    }
                    
                    // Get review count
                    const reviewText = document.body.innerText;
                    const reviewMatch = reviewText.match(/(\\d{1,3}(?:,\\d{3})*)\\s*review/i);
                    if (reviewMatch) {
                        data.reviewCount = parseInt(reviewMatch[1].replace(/,/g, ''));
                    }
                    
                    return data;
                }
            ''')
            
            if page_data.get('name') and not restaurant["name"]:
                restaurant["name"] = page_data.get('name')
            if page_data.get('address') and not restaurant["address"]:
                restaurant["address"] = page_data.get('address')
            if page_data.get('phone') and not restaurant["phone"]:
                restaurant["phone"] = page_data.get('phone')
            if page_data.get('rating') and not restaurant["rating"]:
                restaurant["rating"] = page_data.get('rating')
            if page_data.get('reviewCount') and not restaurant["review_count"]:
                restaurant["review_count"] = page_data.get('reviewCount')
                print(f"    📊 Reviews (fallback): {restaurant['review_count']}")
        except Exception as e:
            print(f"    ⚠️  Error in final fallback: {e}")
            pass
        
        # Print summary of extracted data
        print(f"    📋 Extraction Summary:")
        print(f"       Name: {'✅' if restaurant.get('name') else '❌'}")
        print(f"       Rating: {'✅' if restaurant.get('rating') else '❌'}")
        print(f"       Reviews: {'✅' if restaurant.get('review_count') else '❌'}")
        print(f"       Address: {'✅' if restaurant.get('address') else '❌'}")
        print(f"       Phone: {'✅' if restaurant.get('phone') else '❌'}")
        print(f"       Photos: {len(restaurant.get('images', []))}")
        print(f"       Dishes: {len(restaurant.get('popular_dishes', []))}")
        
    except Exception as e:
        error_msg = str(e)
        if "Timeout" in error_msg:
            print(f"    ⚠️  Timeout error (page may have loaded partially): {error_msg}")
            # Try to extract what we can even if there was a timeout
            try:
                # Quick extraction attempt
                name_elem = page.query_selector('h1.y-css-olzveb')
                if name_elem:
                    restaurant["name"] = name_elem.inner_text().strip()
            except:
                pass
        else:
            print(f"    ⚠️  Error scraping page: {e}")
    
    return restaurant

def scrape_all_restaurants(links_file: str = "yelp_restaurant_links.json", output_file: str = "yelp_restaurant_details.json", images_only: bool = False):
    """Scrape details from all restaurant links, updating JSON after each restaurant"""
    
    # Load restaurant links
    print("📂 Loading restaurant links...")
    with open(links_file, 'r', encoding='utf-8') as f:
        links = json.load(f)
    
    print(f"✅ Loaded {len(links)} restaurant links")
    print()
    
    # Clean URLs (remove query parameters for consistency)
    clean_links = []
    seen = set()
    for link in links:
        clean_url = link.split('?')[0].split('#')[0]
        if clean_url not in seen:
            seen.add(clean_url)
            clean_links.append(clean_url)
    
    print(f"📊 {len(clean_links)} unique restaurants to scrape")
    print()
    
    # Load existing data if file exists
    existing_restaurants = []
    scraped_urls = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_restaurants = json.load(f)
                scraped_urls = {r.get('url', '').split('?')[0].split('#')[0] for r in existing_restaurants if r.get('url')}
            print(f"📂 Found existing file with {len(existing_restaurants)} restaurants")
            print(f"⏭️  Will skip {len(scraped_urls)} already scraped restaurants")
            print()
        except Exception as e:
            print(f"⚠️  Could not load existing file: {e}")
            existing_restaurants = []
            scraped_urls = set()
    
    brave_path = find_brave_path()
    if not brave_path:
        print("⚠️  Brave browser not found. Using system default...")
        brave_path = None
    
    restaurants = existing_restaurants.copy()
    new_count = 0
    skipped_count = 0
    
    with sync_playwright() as p:
        print("🚀 Starting Brave browser...")
        
        launch_options = {
            "headless": False,
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        }
        
        if brave_path:
            launch_options["executable_path"] = brave_path
        
        browser = p.chromium.launch(**launch_options)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            for i, url in enumerate(clean_links, 1):
                clean_url = url.split('?')[0].split('#')[0]
                
                # Find existing restaurant data
                existing_restaurant = None
                existing_index = None
                for idx, r in enumerate(restaurants):
                    if r.get("url", "").split('?')[0].split('#')[0] == clean_url:
                        existing_restaurant = r
                        existing_index = idx
                        break
                
                if images_only:
                    # Only download images for existing restaurants
                    if not existing_restaurant:
                        skipped_count += 1
                        print()
                        print("="*60)
                        print(f"Restaurant {i}/{len(clean_links)}: {url}")
                        print("="*60)
                        print("⏭️  Not in existing data, skipping...")
                        continue
                    
                    print()
                    print("="*60)
                    print(f"Restaurant {i}/{len(clean_links)}: {existing_restaurant.get('name', 'Unknown')}")
                    print(f"URL: {url}")
                    print("="*60)
                    print("📥 Downloading images only...")
                    
                    try:
                        # Navigate to page
                        page.goto(url, wait_until="load", timeout=45000)
                        time.sleep(2)
                        
                        # Extract and download images
                        try:
                            # Click photos link
                            photos_link = page.query_selector('a[href*="/biz_photos"]')
                            if photos_link:
                                print("    📷 Clicking photos link...")
                                photos_link.click()
                                time.sleep(3)
                                
                                # Click Food tab
                                food_tab_clicked = page.evaluate('''
                                    () => {
                                        const tabs = document.querySelectorAll('[role="tab"]');
                                        for (let i = 0; i < tabs.length; i++) {
                                            const tab = tabs[i];
                                            const text = tab.innerText || tab.textContent || '';
                                            if (text.includes('Food') && !text.includes('All')) {
                                                tab.click();
                                                return true;
                                            }
                                        }
                                        if (tabs.length >= 2) {
                                            tabs[1].click();
                                            return true;
                                        }
                                        return false;
                                    }
                                ''')
                                
                                if food_tab_clicked:
                                    print("    🍽️  Clicked Food tab...")
                                    time.sleep(3)
                                
                                # Extract image URLs
                                img_selectors = [
                                    'img.y-css-3xip89',
                                    'img[src*="s3-media"]',
                                    'img[src*="yelpcdn"]',
                                ]
                                
                                image_urls = []
                                seen_srcs = set()
                                
                                for selector in img_selectors:
                                    img_elems = page.query_selector_all(selector)
                                    if img_elems:
                                        for img in img_elems:
                                            src = img.get_attribute('src') or img.get_attribute('data-src')
                                            if src:
                                                if '/348s.jpg' in src:
                                                    src = src.replace('/348s.jpg', '.jpg')
                                                elif '/258s.jpg' in src:
                                                    src = src.replace('/258s.jpg', '.jpg')
                                                if '?' in src:
                                                    src = src.split('?')[0]
                                                
                                                if src and 'yelp' in src.lower() and 'bphoto' in src and src not in seen_srcs:
                                                    seen_srcs.add(src)
                                                    image_urls.append(src)
                                                    if len(image_urls) >= 5:
                                                        break
                                    
                                    if len(image_urls) >= 5:
                                        break
                                
                                # Download images
                                if image_urls:
                                    restaurant_name = existing_restaurant.get("name") or "restaurant"
                                    local_paths = download_images(page, image_urls, restaurant_name)
                                    
                                    # Update existing restaurant with downloaded images
                                    restaurants[existing_index]["images"] = local_paths
                                    restaurants[existing_index]["image_urls"] = image_urls
                                    
                                    # Save immediately
                                    with open(output_file, 'w', encoding='utf-8') as f:
                                        json.dump(restaurants, f, indent=2, ensure_ascii=False)
                                    
                                    print(f"    ✅ Downloaded {len(local_paths)} images")
                                    print(f"💾 Updated JSON file")
                                else:
                                    print("    ⚠️  No images found")
                        except Exception as e:
                            print(f"    ⚠️  Error downloading images: {e}")
                        
                        time.sleep(2)
                        continue
                    except Exception as e:
                        print(f"⚠️  Error processing restaurant: {e}")
                        continue
                
                # Normal scraping (if not images_only)
                if clean_url in scraped_urls:
                    skipped_count += 1
                    print()
                    print("="*60)
                    print(f"Restaurant {i}/{len(clean_links)}: {url}")
                    print("="*60)
                    print("⏭️  Already scraped, skipping...")
                    continue
                
                print()
                print("="*60)
                print(f"Restaurant {i}/{len(clean_links)}: {url}")
                print("="*60)
                
                try:
                    restaurant = scrape_restaurant_detail(page, url, download_images_local=True)
                    
                    if restaurant.get("name"):
                        restaurants.append(restaurant)
                        scraped_urls.add(clean_url)
                        new_count += 1
                        
                        # Save to JSON immediately after scraping
                        try:
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(restaurants, f, indent=2, ensure_ascii=False)
                            print(f"💾 Updated JSON file ({len(restaurants)} restaurants saved)")
                        except Exception as e:
                            print(f"⚠️  Error saving JSON: {e}")
                        
                        print(f"✅ Scraped: {restaurant['name']}")
                        print(f"   Rating: {restaurant.get('rating', 'N/A')}")
                        print(f"   Reviews: {restaurant.get('review_count', 'N/A')}")
                        print(f"   Images: {len(restaurant.get('images', []))}")
                        print(f"   Popular Dishes: {len(restaurant.get('popular_dishes', []))}")
                        print(f"   Review Texts: {len(restaurant.get('reviews', []))}")
                        if restaurant.get('menu_link'):
                            print(f"   Menu Link: {restaurant.get('menu_link')}")
                        if restaurant.get('address'):
                            print(f"   Address: {restaurant.get('address', 'N/A')[:50]}...")
                    else:
                        print("⚠️  Could not extract restaurant name - may have timed out")
                        # Still save the partial data if we have a URL
                        if restaurant.get("url"):
                            restaurants.append(restaurant)
                            scraped_urls.add(clean_url)
                            try:
                                with open(output_file, 'w', encoding='utf-8') as f:
                                    json.dump(restaurants, f, indent=2, ensure_ascii=False)
                            except:
                                pass
                except Exception as e:
                    print(f"⚠️  Error processing restaurant: {e}")
                    # Continue to next restaurant
                
                # Small delay between requests
                time.sleep(2)
                
        finally:
            browser.close()
    
    # Final summary
    print()
    print("="*60)
    print("📊 SCRAPING SUMMARY")
    print("="*60)
    print(f"✅ Total restaurants in file: {len(restaurants)}")
    print(f"🆕 Newly scraped: {new_count}")
    print(f"⏭️  Skipped (already scraped): {skipped_count}")
    print(f"💾 Final file: {output_file}")
    print("="*60)
    
    return restaurants

def download_images_from_json(json_file='yelp_restaurant_details.json', output_dir='restaurant_images'):
    """
    Download all images from Yelp restaurant details JSON file using requests.
    This is a simpler alternative to the Playwright-based download.
    """
    import requests
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Load results
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"📥 Downloading images for {len(results)} restaurants...")
    print(f"📁 Output directory: {output_dir}\n")
    
    downloaded = 0
    failed = 0
    
    for i, restaurant in enumerate(results, 1):
        name = restaurant.get('name', f'restaurant_{i}')
        image_urls = restaurant.get('image_urls', []) or restaurant.get('images', [])
        
        if not image_urls:
            print(f"{i}. {name}: ⚠️  No image URLs")
            continue
        
        # Clean filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')[:50]  # Limit length
        
        # Download up to 5 images per restaurant
        for img_idx, image_url in enumerate(image_urls[:5], 1):
            try:
                # Get file extension from URL
                parsed = urlparse(image_url)
                ext = os.path.splitext(parsed.path)[1] or '.jpg'
                if '?' in ext:
                    ext = ext.split('?')[0]
                
                filename = f"{i:02d}_{img_idx:02d}_{safe_name}{ext}"
                filepath = os.path.join(output_dir, filename)
                
                # Skip if already downloaded
                if os.path.exists(filepath):
                    print(f"{i}. {name} (image {img_idx}): ⏭️  Already exists")
                    downloaded += 1
                    continue
                
                # Download image with proper headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.yelp.com/',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                }
                
                response = requests.get(image_url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Save image
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                file_size = os.path.getsize(filepath) / 1024  # KB
                print(f"{i}. {name} (image {img_idx}): ✅ Downloaded ({file_size:.1f} KB)")
                downloaded += 1
                
                # Small delay between downloads
                time.sleep(0.5)
                
            except Exception as e:
                print(f"{i}. {name} (image {img_idx}): ❌ Failed - {e}")
                failed += 1
    
    print(f"\n{'='*60}")
    print(f"📊 DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Downloaded: {downloaded}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Images saved to: {output_dir}/")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    import sys
    
    # Check if user wants to download images only
    if len(sys.argv) > 1 and sys.argv[1] == '--download-images':
        download_images_from_json()
    else:
        # Set images_only=True to only download images for existing restaurants
        scrape_all_restaurants(images_only=False)

