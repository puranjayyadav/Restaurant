"""
Geohash-based caching system for scraped places.
Implements grid-based caching using geohash cells to avoid re-scraping the same areas.
"""

import math
import os
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import ScrapedPlaceCache
from thefuzz import fuzz # For fuzzy name matching
from supabase import create_client # Moved here to avoid circular dependencies in some contexts
from decouple import config

# --- Utils ---

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

def _data_richness_score(place: Dict) -> int:
    """
    Calculate a score for how "rich" a place's data is.
    Used during deduplication to keep the entry with more useful info.
    """
    score = 0
    if place.get('rating'): score += 2
    if place.get('user_ratings_total'): score += 1
    if place.get('hours') or place.get('opening_hours'): score += 5
    if place.get('types') or place.get('categories'): score += 3
    if place.get('formatted_address') or place.get('address'): score += 2
    if place.get('website'): score += 1
    if place.get('photos'): score += 1
    if place.get('price_level') or place.get('price_tier'): score += 1
    if place.get('vibe_tags'): score += 2
    return score

def deduplicate_places(places: List[Dict]) -> List[Dict]:
    """
Deduplicate a list of places based on spatial proximity (50m) and
fuzzy name matching (60% similarity).
Keeps the entry with richer data in case of duplicates.
"""
    unique_places: List[Dict] = []
    
    for p in places:
        is_duplicate = False
        for existing in unique_places:
            # 1. Check Distance (Physics doesn't lie)
            dist = haversine_distance(
                p.get('lat', 0.0), p.get('lng', 0.0),
                existing.get('lat', 0.0), existing.get('lng', 0.0)
            )
            
            if dist < 50:  # If within 50 meters
                # 2. Check Name Similarity (Fuzzy Match)
                name_p = (p.get('name') or '').lower()
                name_existing = (existing.get('name') or '').lower()
                
                # Use token_sort_ratio for better matching of reordered words
                similarity = fuzz.token_sort_ratio(name_p, name_existing)
                
                if similarity > 60:  # If 60% similar name
                    # MERGE THEM: Keep the one with more data
                    if _data_richness_score(p) > _data_richness_score(existing):
                        existing.update(p)  # Update existing with richer data
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            unique_places.append(p)
            
    return unique_places


# Base32 encoding for geohash
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def get_geohash(lat: float, lon: float, precision: int = 7) -> str:
    """
    Calculate geohash for given coordinates.
    
    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
        precision: Geohash precision (default 7 = ~153m x 153m cells)
    
    Returns:
        Geohash string
    """
    # Clamp coordinates
    lat = max(-90.0, min(90.0, lat))
    lon = max(-180.0, min(180.0, lon))
    
    # Initialize bit ranges
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    
    geohash = []
    bits = 0
    bit = 0
    ch = 0
    even = True
    
    while len(geohash) < precision:
        if even:
            # Longitude bit
            mid = (lon_min + lon_max) / 2.0
            if lon >= mid:
                ch |= (1 << (4 - bit))
                lon_min = mid
            else:
                lon_max = mid
        else:
            # Latitude bit
            mid = (lat_min + lat_max) / 2.0
            if lat >= mid:
                ch |= (1 << (4 - bit))
                lat_min = mid
            else:
                lat_max = mid
        
        even = not even
        
        if bit < 4:
            bit += 1
        else:
            geohash.append(BASE32[ch])
            bit = 0
            ch = 0
    
    return ''.join(geohash)


def get_cached_places(geohash: str, query_context: str) -> Optional[List[Dict]]:
    """
    Retrieve cached places for a geohash and query context.
    
    Uses rolling TTL: checks if scraped_at is within last 24 hours.
    
    Args:
        geohash: Geohash cell ID
        query_context: Time context (e.g., "lunch", "morning")
    
    Returns:
        List of cached places if valid cache exists, None otherwise
    """
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    try:
        cache_entry = ScrapedPlaceCache.objects.filter(
            geohash=geohash,
            query_context=query_context,
            scraped_at__gt=cutoff_time
        ).order_by('-scraped_at').first()
        
        if cache_entry:
            # Increment hit count
            cache_entry.hit_count += 1
            cache_entry.save(update_fields=['hit_count'])
            
            places = cache_entry.places_data
            if isinstance(places, list):
                for p in places:
                    if not p.get('notes'):
                        p['notes'] = p.get('description', '')
            return places
    except Exception as e:
        # Log error but don't fail - fall back to scraping
        print(f"ERROR: Cache lookup failed for {geohash}/{query_context}: {e}")
    
    return None


def save_places_to_cache(geohash: str, query_context: str, places: List[Dict]) -> None:
    """
    Save scraped places to cache.
    
    Args:
        geohash: Geohash cell ID
        query_context: Time context (e.g., "lunch", "morning")
        places: List of place dictionaries to cache
    """
    try:
        # Delete old cache entries for this geohash+context (keep only latest)
        ScrapedPlaceCache.objects.filter(
            geohash=geohash,
            query_context=query_context
        ).delete()
        
        # Create new cache entry
        ScrapedPlaceCache.objects.create(
            geohash=geohash,
            query_context=query_context,
            places_data=places,
            hit_count=0
        )
    except Exception as e:
        # Log error but don't fail - caching is optional
        print(f"ERROR: Failed to save cache for {geohash}/{query_context}: {e}")


def is_cache_valid(cache_entry: ScrapedPlaceCache) -> bool:
    """
    Check if cache entry is still valid (within 24 hours).
    
    Args:
        cache_entry: ScrapedPlaceCache instance
    
    Returns:
        True if cache is valid, False otherwise
    """
    cutoff_time = timezone.now() - timedelta(hours=24)
    return cache_entry.scraped_at > cutoff_time


def cleanup_expired_cache(days_old: int = 1) -> int:
    """
    Clean up expired cache entries older than specified days.
    
    Args:
        days_old: Delete entries older than this many days (default 1 = 24 hours)
    
    Returns:
        Number of entries deleted
    """
    cutoff_time = timezone.now() - timedelta(days=days_old)
    
    deleted_count, _ = ScrapedPlaceCache.objects.filter(
        scraped_at__lt=cutoff_time
    ).delete()
    
    return deleted_count


def get_neighbor_geohashes(geohash: str) -> List[str]:
    """
    Get neighboring geohash cells (for future expansion to handle low-density areas).
    
    Args:
        geohash: Center geohash
    
    Returns:
        List of neighbor geohashes (including center)
    """
    # For now, return just the center geohash
    # Future: implement neighbor calculation for dynamic precision
    return [geohash]

def _infer_types_from_name(name: str) -> List[str]:
    """
    Helper to infer place types from a place's name using keywords.
    Used for categorizing Lemon8 curated places.
    """
    inferred_types = []
    name_lower = name.lower()
    
    # Food-related
    if "restaurant" in name_lower or "eatery" in name_lower or "kitchen" in name_lower:
        inferred_types.append("restaurant")
    if "cafe" in name_lower or "coffee" in name_lower:
        inferred_types.append("cafe")
    if "bar" in name_lower or "pub" in name_lower:
        inferred_types.append("bar")
    if "pizza" in name_lower:
        inferred_types.append("pizza_restaurant")
    if "bakery" in name_lower:
        inferred_types.append("bakery")
    if "sushi" in name_lower or "japanese" in name_lower:
        inferred_types.append("japanese_restaurant")
    if "taco" in name_lower or "mexican" in name_lower:
        inferred_types.append("mexican_restaurant")
    if "thai" in name_lower:
        inferred_types.append("thai_restaurant")
    if "ice cream" in name_lower or "gelato" in name_lower:
        inferred_types.append("ice_cream_shop")
        
    # Activity/Place-related
    if "park" in name_lower:
        inferred_types.append("park")
    if "museum" in name_lower:
        inferred_types.append("museum")
    if "gallery" in name_lower or "art" in name_lower:
        inferred_types.append("art_gallery")
    if "shop" in name_lower or "store" in name_lower or "boutique" in name_lower:
        inferred_types.append("store")
    if "market" in name_lower:
        inferred_types.append("market")
        
    if not inferred_types:
        inferred_types.append("point_of_interest")
        
    return inferred_types

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
    supabase = create_client(config("SUPABASE_URL", default=os.getenv("SUPABASE_URL")), config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY")))
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
                    "notes": stop_info.get("description") or stop_info.get("notes") or "",
                    # Vibe/preference data from solver_data
                    "vibe_tags": vibe_tags,
                    "time_bias": solver_data.get("time_bias") or stop_info.get("time_bias") or None,
                    "price_tier": solver_data.get("price_tier"),
                    "duration_minutes": solver_data.get("duration_minutes"),
                    "category_normalized": solver_data.get("category_normalized"),
                    "solver_data": solver_data if solver_data else None,
                }
                
                curated_places.append(curated_place)
        
        # print(f"DEBUG: Found {len(curated_places)} curated places within {radius_km}km")
        return curated_places
        
    except Exception as e:
        print(f"ERROR: Failed to fetch curated places: {e}")
        return []

def get_curated_from_yelp_restaurants(lat: float, lon: float, radius_km: float = 2.0) -> List[Dict]:
    """
    Fetch curated places from yelp_restaurants table (enriched with hours, ratings).
    
    This is the "Enriched Quality" layer - has opening_hours which the solver needs.
    
    Args:
        lat: User latitude
        lon: User longitude
        radius_km: Search radius in kilometers
    
    Returns:
        List of curated place dictionaries
    """
    supabase = create_client(config("SUPABASE_URL", default=os.getenv("SUPABASE_URL")), config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY")))
    curated_places: List[Dict] = []
    
    try:
        # Supabase RPC call for geospatial query
        # This function should be defined in Supabase as an SQL function
        # For example, named 'get_yelp_places_in_radius'
        # The RPC function handles distance filtering and returns enriched data
        response = supabase.rpc('get_yelp_places_in_radius', {
            'user_lat': lat, 
            'user_lon': lon, 
            'search_radius_km': radius_km
        }).execute()

        for item in response.data or []:
            curated_places.append({
                "name": item.get('name'),
                "place_id": item.get('yelp_id'),  # Use Yelp ID as place_id
                "lat": item.get('latitude'),
                "lng": item.get('longitude'),
                "rating": item.get('rating'),
                "user_ratings_total": item.get('review_count'),
                "price_level": item.get('price'),
                "hours": item.get('opening_hours'),
                "types": item.get('categories'), # Yelp categories
                "formatted_address": item.get('address'),
                "website": item.get('url'),
                "is_curated": True,  # FLAG for scoring bonus
                "source": "yelp",
                "vibe_tags": item.get('vibe_tags') or [], # Directly from Yelp data if enriched
                "time_bias": item.get('time_bias'),
                "price_tier": item.get('price_tier'),
                "category_normalized": item.get('category_normalized'),
            })
    except Exception as e:
        print(f"ERROR: Failed to fetch curated Yelp places: {e}")
        # Fallback to direct table query if RPC fails or is not found
        try:
            res = (
                supabase.table("yelp_restaurants")
                .select("*", count="exact")
                .order('yelp_id')
                .limit(20) # Fallback limit
                .execute()
            )
            for item in res.data or []:
                dist_m = haversine_distance(lat, lon, item.get('latitude', 0.0), item.get('longitude', 0.0))
                if dist_m / 1000.0 <= radius_km:
                     curated_places.append({
                        "name": item.get('name'),
                        "place_id": item.get('yelp_id'),
                        "lat": item.get('latitude'),
                        "lng": item.get('longitude'),
                        "rating": item.get('rating'),
                        "user_ratings_total": item.get('review_count'),
                        "price_level": item.get('price'),
                        "hours": item.get('opening_hours'),
                        "types": item.get('categories'),
                        "formatted_address": item.get('address'),
                        "website": item.get('url'),
                        "is_curated": True,
                        "source": "yelp",
                        "vibe_tags": item.get('vibe_tags') or [],
                        "time_bias": item.get('time_bias'),
                        "price_tier": item.get('price_tier'),
                        "category_normalized": item.get('category_normalized'),
                    })
        except Exception as fallback_e:
            print(f"ERROR: Fallback Yelp fetch also failed: {fallback_e}")
    
    # print(f"DEBUG: Found {len(curated_places)} curated Yelp places within {radius_km}km")
    return curated_places


def get_neighborhood_cluster_rpc(
    lat: float, 
    lon: float, 
    radius_meters: float = 1500
) -> Tuple[List[Dict], bool]:
    """
    Fetch places using PostGIS-based Supabase RPC for fast spatial queries.
    
    This function calls the 'get_neighborhood_cluster' RPC which uses ST_DWithin
    for database-level filtering, returning only places within the radius.
    
    Args:
        lat: Center latitude
        lon: Center longitude  
        radius_meters: Search radius in meters (default 1500m)
    
    Returns:
        Tuple of (places list, rpc_success bool)
    """
    try:
        supabase = create_client(
            config("SUPABASE_URL", default=os.getenv("SUPABASE_URL")), 
            config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))
        )
        
        # Call the PostGIS RPC function
        response = supabase.rpc('get_neighborhood_cluster', {
            'center_lat': lat,
            'center_lng': lon,
            'radius_meters': radius_meters
        }).execute()
        
        if response.data:
            # Transform RPC response to match solver's expected format
            places = []
            for item in response.data:
                places.append({
                    'place_id': str(item.get('id')),
                    'name': item.get('name'),
                    'rating': item.get('rating'),
                    'user_ratings_total': item.get('user_ratings_total'),
                    'vibe_tags': item.get('vibe_tags') or [],
                    'categories': item.get('categories') or [],
                    'types': item.get('categories') or [],  # Alias for solver
                    'lat': item.get('lat'),
                    'lng': item.get('lng'),
                    'distance_m': item.get('distance_m'),
                    'notes': item.get('notes') or item.get('description') or '',
                    'is_clustered': True,  # Mark as from PostGIS cluster
                    'source': 'postgis_rpc',
                })
            
            print(f"DEBUG: PostGIS RPC returned {len(places)} places within {radius_meters}m")
            return places, True
        
        return [], True  # RPC succeeded but no results
        
    except Exception as e:
        print(f"WARNING: PostGIS RPC failed (falling back to Python filtering): {e}")
        return [], False
