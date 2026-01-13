"""Scrape article content from Lemon8 article pages"""
import os
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Input and output files
INPUT_FILE = "lemon8_article_links.json"
OUTPUT_FILE = "lemon8_article_links.json"

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

def load_articles():
    """Load articles from JSON file"""
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found!")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

def save_articles(articles):
    """Save articles to JSON file"""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return False

def scrape_article_content(driver, url):
    """Scrape article content from a single page"""
    try:
        print(f"\nVisiting: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(2)
        
        # Wait for article content section to appear
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "article-content"))
            )
        except TimeoutException:
            print(f"  ⚠ Warning: article-content section not found, trying alternative selectors...")
            time.sleep(3)  # Wait a bit more for dynamic content
        
        # Try to find the article-content section
        try:
            article_section = driver.find_element(By.ID, "article-content")
            # Get the HTML content of the section
            article_html = article_section.get_attribute('outerHTML')
            
            if article_html:
                print(f"  ✓ Successfully scraped article content ({len(article_html)} characters)")
                return article_html
            else:
                print(f"  ✗ No content found in article-content section")
                return None
                
        except NoSuchElementException:
            print(f"  ✗ article-content section not found on page")
            return None
            
    except Exception as e:
        print(f"  ✗ Error scraping article: {e}")
        return None

def main():
    """Main scraping function"""
    # Load articles
    articles = load_articles()
    total_articles = len(articles)
    
    print(f"Loaded {total_articles} articles from {INPUT_FILE}")
    print(f"Starting to scrape article content...")
    print(f"Output will be saved to: {OUTPUT_FILE}")
    print(f"{'='*60}")
    
    # Initialize driver
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    
    try:
        scraped_count = 0
        skipped_count = 0
        error_count = 0
        
        for idx, article in enumerate(articles, 1):
            url = article.get("url")
            
            if not url:
                print(f"\n[{idx}/{total_articles}] Skipping article (no URL)")
                skipped_count += 1
                continue
            
            # Check if already scraped
            if "content" in article and article["content"]:
                print(f"\n[{idx}/{total_articles}] Already scraped: {url}")
                scraped_count += 1
                continue
            
            print(f"\n[{idx}/{total_articles}] Scraping article...")
            
            # Scrape the article content
            content = scrape_article_content(driver, url)
            
            # Update article with content
            if content:
                article["content"] = content
                article["scraped_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                scraped_count += 1
            else:
                article["content"] = None
                article["error"] = "Failed to scrape content"
                article["scraped_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                error_count += 1
            
            # Save after each scrape
            if save_articles(articles):
                print(f"  ✓ JSON file updated")
            else:
                print(f"  ⚠ Warning: Failed to save JSON file")
            
            # Small delay between requests
            time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"Scraping completed!")
        print(f"  Total articles: {total_articles}")
        print(f"  Successfully scraped: {scraped_count}")
        print(f"  Already had content: {sum(1 for a in articles if a.get('content')) - scraped_count}")
        print(f"  Errors: {error_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"\nResults saved to: {OUTPUT_FILE}")
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
        print("Saving current progress...")
        save_articles(articles)
        print("Progress saved!")
        
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        print("\nSaving current progress...")
        save_articles(articles)
        
    finally:
        driver.quit()
        print("\nBrowser closed.")

if __name__ == "__main__":
    main()
