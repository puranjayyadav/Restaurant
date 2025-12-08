"""Open Lemon8 NYC Eats page in Brave with auto-scroll and scrape article links"""
import os
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse

url = "https://www.lemon8-app.com/experience/new-york-eat?region=us"

if len(sys.argv) > 1:
    url = sys.argv[1]

print(f"Opening: {url}")
print("Opening in Brave with auto-scroll...")

# Find Brave executable
brave_paths = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
]

brave_path = None
for path in brave_paths:
    if os.path.exists(path):
        brave_path = path
        break

if not brave_path:
    print("Brave not found in standard locations!")
    print("Please install Brave browser or update the path in the script.")
    sys.exit(1)

print(f"Found Brave at: {brave_path}")

# Setup Chrome options for Brave
options = Options()
options.binary_location = brave_path
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

try:
    # Initialize driver
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    
    print("Loading page...")
    driver.get(url)
    
    # Wait for page to load
    print("Waiting for page content to load...")
    time.sleep(3)
    
    # Auto-scroll function
    def auto_scroll(driver, scroll_pause_time=0.5, max_scrolls=50):
        """Smoothly scroll down the page"""
        print("\nStarting auto-scroll...")
        print("Press Ctrl+C to stop scrolling and keep browser open")
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        
        try:
            while scroll_count < max_scrolls:
                # Scroll down smoothly
                driver.execute_script("window.scrollBy(0, 500);")
                scroll_count += 1
                time.sleep(scroll_pause_time)
                
                # Check if new content loaded
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # Try scrolling to bottom to trigger lazy loading
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                
                last_height = new_height
                
                if scroll_count % 10 == 0:
                    print(f"Scrolled {scroll_count} times...")
                    
        except KeyboardInterrupt:
            print("\n\nScrolling stopped by user.")
            print("Browser will remain open for scraping.")
    
    # Start auto-scrolling
    auto_scroll(driver, scroll_pause_time=0.5, max_scrolls=100)
    
    print(f"\n✓ Page opened in Brave: {url}")
    print("✓ Auto-scroll completed!")
    
    # Scrape article links
    print("\nExtracting article links...")
    time.sleep(2)  # Wait a bit for any final content to load
    
    # Find all article cards
    article_links = []
    base_url = "https://www.lemon8-app.com"
    
    try:
        # Find all elements with class "article-recommend-card"
        article_cards = driver.find_elements(By.CSS_SELECTOR, "a.article-recommend-card")
        
        print(f"Found {len(article_cards)} article cards")
        
        seen_links = set()
        for card in article_cards:
            try:
                href = card.get_attribute("href")
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith("/"):
                        full_url = urljoin(base_url, href)
                    elif href.startswith("http"):
                        full_url = href
                    else:
                        full_url = urljoin(base_url, "/" + href)
                    
                    # Remove duplicates
                    if full_url not in seen_links:
                        seen_links.add(full_url)
                        article_links.append({
                            "url": full_url,
                            "relative_path": href
                        })
            except Exception as e:
                print(f"Error extracting link from card: {e}")
                continue
        
        print(f"✓ Extracted {len(article_links)} unique article links")
        
        # Save to JSON file
        output_file = "lemon8_article_links.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(article_links, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved links to {output_file}")
        
        # Also save a simple text file with just URLs
        txt_output_file = "lemon8_article_links.txt"
        with open(txt_output_file, 'w', encoding='utf-8') as f:
            for link_data in article_links:
                f.write(link_data["url"] + "\n")
        
        print(f"✓ Saved URLs to {txt_output_file}")
        
    except Exception as e:
        print(f"Error scraping links: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nBrowser will remain open. You can inspect the page if needed.")
    print("Close the browser window when done, or press Enter to close.")
    
    # Keep browser open - don't call driver.quit()
    input("\nPress Enter to close the browser...")
    driver.quit()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    try:
        driver.quit()
    except:
        pass
    sys.exit(1)
