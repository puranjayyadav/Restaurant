"""Quick test to verify Selenium setup"""
import sys
print("Testing Selenium setup...")
sys.stdout.flush()

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    print("Selenium imported successfully")
    sys.stdout.flush()
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    print("Attempting to start Chrome driver...")
    sys.stdout.flush()
    
    driver = webdriver.Chrome(options=options)
    print("Chrome driver started successfully!")
    sys.stdout.flush()
    
    print("Navigating to test page...")
    sys.stdout.flush()
    driver.get("https://www.google.com")
    print(f"Page title: {driver.title}")
    sys.stdout.flush()
    
    driver.quit()
    print("Test completed successfully!")
    sys.stdout.flush()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    sys.exit(1)
