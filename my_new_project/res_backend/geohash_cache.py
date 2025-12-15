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

