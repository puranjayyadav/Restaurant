"""Run the Lemon8 scraper with error handling"""
import sys
import traceback

# Set up output to be visible
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

print("=" * 60)
print("Starting Lemon8 Scraper")
print("=" * 60)
sys.stdout.flush()

try:
    from scrape_lemon8 import scrape_lemon8_page
    
    url = "https://www.lemon8-app.com/experience/new-york-eats?region=us"
    max_posts = 20
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
    if len(sys.argv) > 2:
        max_posts = int(sys.argv[2])
    
    print(f"\nURL: {url}")
    print(f"Max posts: {max_posts}")
    print("-" * 60)
    sys.stdout.flush()
    
    results = scrape_lemon8_page(url, max_posts=max_posts, scroll_to_load=True)
    
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE!")
    print(f"Total posts found: {len(results)}")
    print(f"{'='*60}")
    sys.stdout.flush()
    
except KeyboardInterrupt:
    print("\n\nScraping interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n\nERROR: {e}")
    traceback.print_exc()
    sys.stdout.flush()
    sys.exit(1)
