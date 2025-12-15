"""
Service for cached scraping of places.
Integrates geohash caching with Google Maps scraping.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from django.utils import timezone
import sys
import os

# Add parent directory to path for google_maps_scraper import
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from google_maps_scraper import get_google_maps_data
from .geohash_cache import (
    get_geohash, get_cached_places, save_places_to_cache
)
from .utils import get_time_context_query, get_time_context_label


def get_cached_or_scraped_places(
    lat: float,
    lon: float,
    query: Optional[str] = None,
    use_time_context: bool = True,
    radius_km: float = 1.0
) -> Tuple[List[Dict], bool]:
    """
    Get places from cache if available, otherwise scrape and cache.
    
    Args:
        lat: Latitude
        lon: Longitude
        query: Optional search query (if None, uses time-context query)
        use_time_context: If True, use time-based query keywords
        radius_km: Search radius in kilometers
    
    Returns:
        Tuple of (places_list, cache_hit_boolean)
    """
    # Calculate geohash
    geohash = get_geohash(lat, lon, precision=7)
    
    # Get time context
    current_time = timezone.now()
    time_context = get_time_context_label(current_time.hour)
    query_context = time_context
    
    # Check cache
    cached_places = get_cached_places(geohash, query_context)
    
    if cached_places is not None:
        print(f"DEBUG: Cache HIT for {geohash}/{query_context}: {len(cached_places)} places")
        return cached_places, True
    
    # Cache miss - scrape
    print(f"DEBUG: Cache MISS for {geohash}/{query_context}, scraping...")
    
    # Determine query
    if query is None and use_time_context:
        time_queries = get_time_context_query(current_time.hour)
        # Use first query as primary
        query = time_queries[0] if time_queries else "restaurant"
    
    if query is None:
        query = "restaurant"
    
    # Calculate zoom based on radius
    zoom = 13499.795714815926  # Default
    if radius_km <= 0.5:
        zoom = 2000
    elif radius_km <= 1.0:
        zoom = 4000
    elif radius_km <= 2.0:
        zoom = 10000
    elif radius_km <= 5.0:
        zoom = 35000
    else:
        zoom = 70000
    
    # Scrape
    places = get_google_maps_data(
        query=query,
        lat=lat,
        lon=lon,
        zoom=zoom,
        count=200
    )
    
    # Save to cache
    if places:
        save_places_to_cache(geohash, query_context, places)
        print(f"DEBUG: Saved {len(places)} places to cache: {geohash}/{query_context}")
    
    return places, False

