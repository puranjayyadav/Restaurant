"""Quick test script to run Lemon8 scraper"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrape_lemon8 import scrape_lemon8_page

if __name__ == "__main__":
    # Test URL - you can change this
    test_url = "https://www.lemon8-app.com/hashtag/food"
    max_posts = 10
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    if len(sys.argv) > 2:
        max_posts = int(sys.argv[2])
    
    print(f"Starting scraper with URL: {test_url}")
    print(f"Max posts: {max_posts}")
    print("-" * 60)
    
    try:
        results = scrape_lemon8_page(test_url, max_posts=max_posts, scroll_to_load=True)
        print(f"\nScraping completed! Found {len(results)} posts")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
