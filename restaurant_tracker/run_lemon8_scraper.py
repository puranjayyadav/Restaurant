"""Run Lemon8 scraper with file-based logging"""
import sys
import os
import traceback

# Redirect stdout and stderr to a file
log_file = open('lemon8_scraper_run.log', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

print("=" * 60)
print("Lemon8 Scraper - Starting")
print("=" * 60)
log_file.flush()

try:
    from scrape_lemon8 import scrape_lemon8_page
    
    url = "https://www.lemon8-app.com/hashtag/food"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    max_posts = 5
    if len(sys.argv) > 2:
        max_posts = int(sys.argv[2])
    
    print(f"URL: {url}")
    print(f"Max posts: {max_posts}")
    print("-" * 60)
    log_file.flush()
    
    results = scrape_lemon8_page(url, max_posts=max_posts, scroll_to_load=True)
    
    print(f"\nCompleted! Found {len(results)} posts")
    log_file.flush()
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
    log_file.flush()
finally:
    log_file.close()
    # Also print to console
    with open('lemon8_scraper_run.log', 'r', encoding='utf-8') as f:
        print(f.read())
