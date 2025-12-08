"""Open URL in default browser"""
import webbrowser
import sys

url = "https://www.lemon8-app.com/experience/new-york-eats?region=us"

if len(sys.argv) > 1:
    url = sys.argv[1]

print(f"Opening URL: {url}")
print("This should open in your default browser...")

# Try to open in Chrome specifically
try:
    chrome_path = None
    import os
    
    # Common Chrome paths
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_path = path
            break
    
    if chrome_path:
        print(f"Found Chrome at: {chrome_path}")
        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
        webbrowser.get('chrome').open(url)
        print("Opened in Chrome!")
    else:
        print("Chrome not found, using default browser...")
        webbrowser.open(url)
        print("Opened in default browser!")
        
except Exception as e:
    print(f"Error: {e}")
    print("Trying default browser...")
    webbrowser.open(url)
