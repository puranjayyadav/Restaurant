"""
Service for cached scraping of places.
Integrates geohash caching with Google Maps scraping.
"""

import math
import os
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from django.utils import timezone
import sys

# Import Supabase client
from supabase import create_client

# Add parent directory to path for google_maps_scraper import
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from google_maps_scraper import get_google_maps_data
from .geohash_cache import (
    get_geohash, get_cached_places, save_places_to_cache
)
from .utils import get_time_context_query, get_time_context_label, haversine_distance, _infer_types_from_name

def get_curated_places_from_lemon8(lat: float, lon: float, radius_km: float = 2.0) -> List[Dict]:
    """
    Fetch curated places from lemon8_articles table (from enriched_itinerary_data).

    These are hand-picked high-quality places from Lemon8 itineraries.

    Args:
        lat: User latitude
        lon: User longitude
        radius_km: Search radius in kilometers
    Returns:
        List of curated place dictionaries
    """
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    curated_places: List[Dict] = []
    seen_names: Set[str] = set()  # To prevent duplicate curated places from different articles
    
    try:
        # Fetch all articles with enriched data. We filter by proximity in Python for flexibility.
        response = (
            supabase.table("lemon8_articles")
            .select("url, enriched_itinerary_data")
            .not_.is_("enriched_itinerary_data", "null")
            .execute()
        )
        
        for row in response.data or []:
            article_url = row.get("url")
            itinerary_data = row.get("enriched_itinerary_data")
            
            # Handle potential list wrapper around itinerary_data
            if isinstance(itinerary_data, list) and itinerary_data:
                itinerary_data = itinerary_data[0]
            
            if not itinerary_data or "stops" not in itinerary_data:
                continue
                
            stops = itinerary_data["stops"]
            
            for i, stop in enumerate(stops):
                stop_lat = stop.get("lat") or stop.get("latitude")
                stop_lng = stop.get("lng") or stop.get("longitude")
                
                if stop_lat is None or stop_lng is None:
                    continue
                    
                # Calculate distance
                dist_m = haversine_distance(lat, lon, float(stop_lat), float(stop_lng))
                dist_km = dist_m / 1000.0
                
                if dist_km > radius_km:
                    continue  # Too far
                
                # Get stop metadata if available
                stop_info = stop
                stop_name = stop_info.get("name") or stop_info.get("place_name") or f"Stop {i+1}"
                
                # Extract solver_data (contains vibe_tags, time_bias, price_tier, etc.)
                solver_data = stop_info.get("solver_data") or {}
                
                # Deduplicate based on name (within curated list itself)
                name_key = stop_name.lower().strip()
                if name_key in seen_names:
                    continue
                seen_names.add(name_key)
                
                # Extract vibe_tags from solver_data (primary) or stop_info (fallback)
                vibe_tags = (
                    solver_data.get("vibe_tags") or 
                    stop_info.get("vibe_tags") or 
                    stop_info.get("tags") or 
                    []
                )
                
                # Build curated place dict with FULL solver_data extraction
                curated_place = {
                    "name": stop_name,
                    "lat": float(stop_lat),
                    "lng": float(stop_lng),
                    "place_id": f"lemon8_{hash(stop_name + str(stop_lat))}",  # Synthetic ID
                    "is_curated": True,  # FLAG for scoring bonus
                    "source": "lemon8",
                    "source_url": article_url,
                    "rating": stop_info.get("rating") or 4.5,  # Default good rating for curated
                    "types": _infer_types_from_name(stop_name),
                    "custom_notes": stop_info.get("description") or stop_info.get("notes") or "",
                    # Vibe/preference data from solver_data
                    "vibe_tags": vibe_tags,
                    "time_bias": solver_data.get("time_bias") or stop_info.get("time_bias") or None,
                    "price_tier": solver_data.get("price_tier"),
                    "category_normalized": solver_data.get("category_normalized"),
                    "solver_data": solver_data if solver_data else None,
                }
                
                curated_places.append(curated_place)
        
        # print(f"DEBUG: Found {len(curated_places)} curated places within {radius_km}km")
        return curated_places
        
    except Exception as e:
        print(f"ERROR: Failed to fetch curated places: {e}")
        return []

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
