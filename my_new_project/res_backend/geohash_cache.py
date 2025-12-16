"""
Geohash-based caching system for scraped places.
Uses Supabase table-based cache instead of Django ORM.
"""

import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
import os
import sys

# Ensure workspace root on path to import supabase_config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from supabase_config import get_supabase_client


# Base32 encoding for geohash
BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

# Supabase table for cache
CACHE_TABLE = "cached_places"


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
    
    supabase = get_supabase_client()
    if not supabase:
        return None

    try:
        res = (
            supabase.table(CACHE_TABLE)
            .select("*")
            .eq("geohash", geohash)
            .eq("query_context", query_context)
            .gt("scraped_at", cutoff_time.isoformat())
            .order("scraped_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if rows:
            entry = rows[0]
            # best-effort hit count increment
            try:
                hit = int(entry.get("hit_count") or 0) + 1
                supabase.table(CACHE_TABLE).update({"hit_count": hit}).eq("geohash", geohash).eq("query_context", query_context).execute()
            except Exception:
                pass
            return entry.get("places_data")
    except Exception as e:
        print(f"ERROR: Supabase cache lookup failed for {geohash}/{query_context}: {e}")
    return None


def save_places_to_cache(geohash: str, query_context: str, places: List[Dict]) -> None:
    """
    Save scraped places to cache.
    
    Args:
        geohash: Geohash cell ID
        query_context: Time context (e.g., "lunch", "morning")
        places: List of place dictionaries to cache
    """
    supabase = get_supabase_client()
    if not supabase:
        return

    try:
        # Upsert by (geohash, query_context)
        payload = {
            "geohash": geohash,
            "query_context": query_context,
            "places_data": places,
            "scraped_at": datetime.utcnow().isoformat(),
            "hit_count": 0,
        }
        supabase.table(CACHE_TABLE).upsert(payload, on_conflict="geohash,query_context").execute()
    except Exception as e:
        print(f"ERROR: Failed to save Supabase cache for {geohash}/{query_context}: {e}")


def is_cache_valid(scraped_at: datetime) -> bool:
    """Check if cache entry is still valid (within 24 hours)."""
    cutoff_time = timezone.now() - timedelta(hours=24)
    return scraped_at > cutoff_time


def cleanup_expired_cache(days_old: int = 1) -> int:
    """
    Clean up expired cache entries older than specified days.
    
    Args:
        days_old: Delete entries older than this many days (default 1 = 24 hours)
    
    Returns:
        Number of entries deleted
    """
    supabase = get_supabase_client()
    if not supabase:
        return 0
    cutoff_time = (timezone.now() - timedelta(days=days_old)).isoformat()
    try:
        # Supabase doesn't support delete returning count directly; perform select then delete
        res = supabase.table(CACHE_TABLE).select("geohash,query_context").lt("scraped_at", cutoff_time).execute()
        rows = res.data or []
        for row in rows:
            supabase.table(CACHE_TABLE).delete().eq("geohash", row["geohash"]).eq("query_context", row["query_context"]).execute()
        return len(rows)
    except Exception as e:
        print(f"ERROR: cleanup_expired_cache failed: {e}")
        return 0


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


# ============================================================================
# Curated Data Functions (Hybrid Data Strategy)
# ============================================================================

def get_curated_places_from_lemon8(lat: float, lon: float, radius_km: float = 2.0) -> List[Dict]:
    """
    Fetch curated places from lemon8_articles stops near the given location.
    
    This is the "Permanent Quality" layer of the hybrid data system.
    These are hand-picked spots from real itineraries, not scraped at scale.
    
    Args:
        lat: User latitude
        lon: User longitude
        radius_km: Search radius in km (default 2km)
    
    Returns:
        List of curated place dicts ready for the solver
    """
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        # Get articles that have geocoded stops
        res = (
            supabase.table("lemon8_articles")
            .select("url, enriched_itinerary_data, stops_lat, stops_lng")
            .not_.is_("stops_lat", "null")
            .not_.is_("stops_lng", "null")
            .execute()
        )
        
        rows = res.data or []
        curated_places = []
        seen_names = set()  # Deduplicate by name
        
        for row in rows:
            stops_lat = row.get("stops_lat") or []
            stops_lng = row.get("stops_lng") or []
            itinerary_data = row.get("enriched_itinerary_data") or {}
            
            # Handle list vs dict format
            if isinstance(itinerary_data, list) and itinerary_data:
                itinerary_data = itinerary_data[0]
            
            stops = itinerary_data.get("stops") or []
            article_url = row.get("url")
            
            for i, (stop_lat, stop_lng) in enumerate(zip(stops_lat, stops_lng)):
                if stop_lat is None or stop_lng is None:
                    continue
                
                # Calculate distance to user
                from .utils import haversine_distance
                dist_m = haversine_distance(lat, lon, float(stop_lat), float(stop_lng))
                dist_km = dist_m / 1000.0
                
                if dist_km > radius_km:
                    continue  # Too far
                
                # Get stop metadata if available
                stop_info = stops[i] if i < len(stops) else {}
                stop_name = stop_info.get("name") or stop_info.get("place_name") or f"Stop {i+1}"
                
                # Extract solver_data (contains vibe_tags, time_bias, price_tier, etc.)
                solver_data = stop_info.get("solver_data") or {}
                
                # Deduplicate
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
                    "duration_minutes": solver_data.get("duration_minutes"),
                    "category_normalized": solver_data.get("category_normalized"),
                    # Keep full solver_data for advanced matching
                    "solver_data": solver_data if solver_data else None,
                }
                
                curated_places.append(curated_place)
        
        print(f"DEBUG: Found {len(curated_places)} curated places within {radius_km}km")
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
        radius_km: Search radius in km
    
    Returns:
        List of enriched curated place dicts
    """
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        # Get yelp restaurants that have location data
        res = (
            supabase.table("yelp_restaurants")
            .select("*")
            .not_.is_("location", "null")
            .execute()
        )
        
        rows = res.data or []
        curated_places = []
        
        for row in rows:
            location = row.get("location") or {}
            rest_lat = location.get("lat") or location.get("latitude")
            rest_lng = location.get("lng") or location.get("longitude") or location.get("lon")
            
            if rest_lat is None or rest_lng is None:
                continue
            
            # Calculate distance
            from .utils import haversine_distance
            dist_m = haversine_distance(lat, lon, float(rest_lat), float(rest_lng))
            dist_km = dist_m / 1000.0
            
            if dist_km > radius_km:
                continue
            
            # Build enriched place dict
            curated_place = {
                "name": row.get("name") or "Unknown",
                "lat": float(rest_lat),
                "lng": float(rest_lng),
                "place_id": row.get("yelp_id") or f"yelp_{hash(row.get('name', ''))}",
                "is_curated": True,
                "source": "yelp",
                "source_url": row.get("url"),
                "rating": row.get("rating") or 4.0,
                "types": row.get("categories") or [],
                "hours": row.get("hours"),  # Critical for open-now filtering
                "opening_hours": row.get("hours"),
                "address": row.get("address") or "",
                "price_range": row.get("price_range"),
                "custom_notes": row.get("description") or "",
                "vibe_tags": [],  # Can be enriched from lemon8 cross-reference
            }
            
            curated_places.append(curated_place)
        
        print(f"DEBUG: Found {len(curated_places)} Yelp curated places within {radius_km}km")
        return curated_places
        
    except Exception as e:
        print(f"ERROR: Failed to fetch Yelp curated places: {e}")
        return []


def spatial_deduplicate_places(places: List[Dict], distance_threshold_m: float = 50.0, name_similarity_threshold: float = 0.6) -> List[Dict]:
    """
    Deduplicate places using spatial proximity + fuzzy name matching.
    
    The "Doppelgänger Bug" fix: "Da Andrea - Chelsea" and "Da Andrea" at same location
    should be merged, not treated as separate places.
    
    Args:
        places: List of place dicts with lat/lng
        distance_threshold_m: Max distance in meters to consider same place (default 50m)
        name_similarity_threshold: Min name similarity ratio (0-1) to merge (default 0.6)
    
    Returns:
        Deduplicated list, keeping the place with most data (hours, types, etc.)
    """
    from difflib import SequenceMatcher
    from .utils import haversine_distance
    
    if not places:
        return []
    
    unique_places = []
    merged_count = 0
    
    for p in places:
        p_lat = p.get('lat')
        p_lng = p.get('lng')
        p_name = (p.get('name') or '').lower().strip()
        
        if p_lat is None or p_lng is None:
            unique_places.append(p)
            continue
        
        is_duplicate = False
        
        for existing in unique_places:
            e_lat = existing.get('lat')
            e_lng = existing.get('lng')
            
            if e_lat is None or e_lng is None:
                continue
            
            # 1. Check Distance (Physics doesn't lie)
            dist = haversine_distance(float(p_lat), float(p_lng), float(e_lat), float(e_lng))
            
            if dist < distance_threshold_m:
                # 2. Check Name Similarity
                e_name = (existing.get('name') or '').lower().strip()
                similarity = SequenceMatcher(None, p_name, e_name).ratio()
                
                if similarity > name_similarity_threshold:
                    # MERGE: Keep the one with more data
                    # Prefer: has hours > has more types > is_curated > higher rating
                    p_score = _data_richness_score(p)
                    e_score = _data_richness_score(existing)
                    
                    if p_score > e_score:
                        # New place has more data, update existing with it
                        # But preserve existing's place_id if it's a Google ID (starts with ChIJ)
                        old_id = existing.get('place_id', '')
                        existing.update(p)
                        if old_id.startswith('ChIJ'):
                            existing['place_id'] = old_id
                    
                    merged_count += 1
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            unique_places.append(p)
    
    if merged_count > 0:
        print(f"DEBUG: Spatial dedup merged {merged_count} duplicate places (threshold={distance_threshold_m}m)")
    
    return unique_places


def _data_richness_score(place: Dict) -> int:
    """Score how much useful data a place has (for merge priority)."""
    score = 0
    if place.get('hours') or place.get('opening_hours'):
        score += 10  # Hours are critical
    if place.get('types') and len(place.get('types', [])) > 1:
        score += 3
    if place.get('is_curated'):
        score += 5
    if place.get('rating') and float(place.get('rating', 0)) > 0:
        score += 2
    if place.get('address'):
        score += 1
    if place.get('source') == 'yelp':
        score += 3  # Yelp data is richer
    return score


def get_combined_places(
    lat: float, 
    lon: float, 
    scraped_places: List[Dict],
    radius_km: float = 2.0
) -> Tuple[List[Dict], Dict]:
    """
    Merge Curated Data (Quality) with Scraped Data (Quantity).
    
    Uses spatial deduplication to avoid the "Doppelgänger Bug" where
    the same place appears twice with slightly different names.
    
    Args:
        lat: User latitude
        lon: User longitude
        scraped_places: List of scraped places from Google cache
        radius_km: Search radius for curated data
    
    Returns:
        Tuple of (combined_places_list, stats_dict)
    """
    combined = []
    seen_ids = set()
    seen_names = set()
    
    stats = {"curated_lemon8": 0, "curated_yelp": 0, "scraped": 0, "duplicates_skipped": 0, "spatial_merged": 0}
    
    # 1. First, add Yelp curated (best quality - has hours)
    yelp_curated = get_curated_from_yelp_restaurants(lat, lon, radius_km)
    for place in yelp_curated:
        place_id = place.get("place_id")
        name_key = (place.get("name") or "").lower().strip()
        
        if place_id and place_id in seen_ids:
            stats["duplicates_skipped"] += 1
            continue
        if name_key and name_key in seen_names:
            stats["duplicates_skipped"] += 1
            continue
        
        combined.append(place)
        if place_id:
            seen_ids.add(place_id)
        if name_key:
            seen_names.add(name_key)
        stats["curated_yelp"] += 1
    
    # 2. Add Lemon8 curated (good quality - hand-picked but may lack hours)
    lemon8_curated = get_curated_places_from_lemon8(lat, lon, radius_km)
    for place in lemon8_curated:
        place_id = place.get("place_id")
        name_key = (place.get("name") or "").lower().strip()
        
        if place_id and place_id in seen_ids:
            stats["duplicates_skipped"] += 1
            continue
        if name_key and name_key in seen_names:
            stats["duplicates_skipped"] += 1
            continue
        
        combined.append(place)
        if place_id:
            seen_ids.add(place_id)
        if name_key:
            seen_names.add(name_key)
        stats["curated_lemon8"] += 1
    
    # 3. Add scraped places (quantity - fill gaps)
    for place in scraped_places:
        place_id = place.get("place_id")
        name_key = (place.get("name") or "").lower().strip()
        
        if place_id and place_id in seen_ids:
            stats["duplicates_skipped"] += 1
            continue
        if name_key and name_key in seen_names:
            stats["duplicates_skipped"] += 1
            continue
        
        # Mark as not curated
        place["is_curated"] = False
        combined.append(place)
        if place_id:
            seen_ids.add(place_id)
        if name_key:
            seen_names.add(name_key)
        stats["scraped"] += 1
    
    # 4. SPATIAL DEDUPLICATION - Fix the "Doppelgänger Bug"
    # Merge places within 50m that have similar names
    pre_dedup_count = len(combined)
    combined = spatial_deduplicate_places(combined, distance_threshold_m=50.0, name_similarity_threshold=0.6)
    stats["spatial_merged"] = pre_dedup_count - len(combined)
    
    print(f"DEBUG: Combined places - Yelp:{stats['curated_yelp']}, Lemon8:{stats['curated_lemon8']}, Scraped:{stats['scraped']}, String-Dupes:{stats['duplicates_skipped']}, Spatial-Merged:{stats['spatial_merged']}")
    
    return combined, stats


def _infer_types_from_name(name: str) -> List[str]:
    """Infer place types from name for basic categorization."""
    name_lower = name.lower()
    types = []
    
    type_keywords = {
        "bar": ["bar", "pub", "tavern", "lounge"],
        "cafe": ["cafe", "café", "coffee", "espresso"],
        "restaurant": ["restaurant", "bistro", "grill", "kitchen", "eatery"],
        "bakery": ["bakery", "bakehouse", "patisserie"],
        "pizza": ["pizza", "pizzeria"],
        "sushi": ["sushi", "japanese"],
        "mexican": ["taco", "mexican", "taqueria"],
        "chinese": ["chinese", "dim sum", "dumpling"],
        "italian": ["italian", "trattoria", "osteria"],
        "museum": ["museum", "gallery"],
        "park": ["park", "garden"],
    }
    
    for category, keywords in type_keywords.items():
        if any(kw in name_lower for kw in keywords):
            types.append(category)
    
    return types if types else ["restaurant"]  # Default