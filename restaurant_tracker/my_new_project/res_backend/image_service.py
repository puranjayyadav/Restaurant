"""
Pexels Image Service
The 'Concierge' Choice: Higher limits, polished aesthetic.
"""
import os
import json
import hashlib
import requests
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
    # Go up from res_backend/ to my_new_project/ to root/
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')
except ImportError:
    PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')

logger = logging.getLogger(__name__)

# Debug: Print if API key was loaded
if PEXELS_API_KEY:
    print(f"[ImageService] Pexels API key loaded ({len(PEXELS_API_KEY)} chars)")
else:
    print("[ImageService] WARNING: PEXELS_API_KEY not found!")

# Cache settings
CACHE_DIR = Path(__file__).parent / 'data' / 'image_cache'
CACHE_EXPIRY_DAYS = 7

class PexelsService:
    """
    Fetches premium images from Pexels.
    Pros: 20k reqs/month free, very consistent 'luxury' quality.
    """
    BASE_URL = "https://api.pexels.com/v1/search"

    # Pexels loves "literal" luxury terms.
    VIBE_KEYWORDS = {
        "coffee": "barista espresso latte art luxury cafe",
        "nightlife": "cocktail bar dark atmosphere night club luxury",
        "food": "fine dining plated food chef michelin",
        "dinner": "candlelight dinner romantic restaurant evening",
        "lunch": "brunch table spread gourmet food",
        "shopping": "luxury boutique fashion store interior",
        "nature": "moody forest park dark green cinematic",
    }

    def __init__(self):
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_venue_image(self, venue_name: str, category: str, vibe: str, city: str = "New York", exclude_urls: List[str] = None) -> str:
        exclude_urls = exclude_urls or []
        # 1. Check Cache
        cache_key = self._get_cache_key(venue_name, category, vibe)
        cached_url = self._get_from_cache(cache_key)
        
        # Only return cached if it's not in the excluded list
        if cached_url and cached_url not in exclude_urls:
            return cached_url

        # 2. Search Strategy (Cascading)
        vibe_key = vibe.lower()
        aesthetic = self.VIBE_KEYWORDS.get(vibe_key, f"{vibe} luxury")

        queries = [
            # Attempt 1: The "Real" Place
            f"{venue_name} {city}",
            
            # Attempt 2: The "Concierge" Shot (Vibe + Category)
            f"{category} {aesthetic} interior",
            
            # Attempt 3: The "Atmosphere" Fallback
            f"{category} dark moody aesthetic",
        ]

        logger.info(f"Fetching Pexels image for {venue_name}...")

        for query in queries:
            image_url = self._fetch_image(query, exclude_urls)
            if image_url:
                self._save_to_cache(cache_key, image_url)
                return image_url

        # Ultimate Fallback (A dark, moody abstract texture)
        fallback = "https://images.pexels.com/photos/3374210/pexels-photo-3374210.jpeg?auto=compress&cs=tinysrgb&w=800"
        return fallback

    def _fetch_image(self, query: str, exclude_urls: List[str] = None) -> str | None:
        if not PEXELS_API_KEY:
            return None
        
        exclude_urls = exclude_urls or []
        headers = {
            "Authorization": PEXELS_API_KEY
        }
        
        params = {
            "query": query,
            "per_page": 8,     # Get more for better variety
            "orientation": "square",
            "size": "medium",
            "locale": "en-US"
        }

        try:
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=4)
            
            if response.status_code == 200:
                data = response.json()
                photos = data.get('photos', [])
                
                # Filter out excluded URLs
                available = [p for p in photos if p['src']['large'] not in exclude_urls]
                
                if available:
                    # Pick a random one from top available for variety
                    chosen = random.choice(available[:3])
                    return chosen['src']['large']
            
            return None

        except Exception as e:
            logger.error(f"Pexels Error: {e}")
            return None

    def _get_cache_key(self, venue_name: str, category: str, vibe: str) -> str:
        # Include 'pexels' in key to distinguish from old unsplash cache
        raw_key = f"pexels:{venue_name}:{category}:{vibe}".lower()
        return hashlib.md5(raw_key.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> str | None:
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                cached_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cached_time < timedelta(days=CACHE_EXPIRY_DAYS):
                    return data['url']
                else:
                    cache_file.unlink()
            except:
                pass
        return None

    def _save_to_cache(self, cache_key: str, url: str) -> None:
        try:
            with open(self.cache_dir / f"{cache_key}.json", 'w') as f:
                json.dump({'url': url, 'timestamp': datetime.now().isoformat()}, f)
        except:
            pass

# Singleton
image_service = PexelsService()
