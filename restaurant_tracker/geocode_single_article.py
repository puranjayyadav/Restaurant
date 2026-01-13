"""
Geocode a specific Lemon8 article by URL.
"""
import os
import time
import re
import json
from typing import Dict, Any, List, Optional

import requests
from supabase_config import get_supabase_client

# --- Configuration ---
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "1.1"))  # Critical for Nominatim
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "").strip()

# If your app is US-only, keep this 'us'. If global, remove it or make it dynamic.
TARGET_COUNTRY_CODE = "us" 


def clean_search_term(name: str) -> str:
    """
    Aggressive cleaning to fix 'HOJOKBAN NYC', 'Lido Harlem Restaurant', 'Hani's +'.
    Removes specific noise words that confuse strict geocoders.
    """
    if not name:
        return ""

    original_name = name

    # 1. Remove special separators and replace with space
    name = re.sub(r'[|+\-:]', ' ', name)

    # 2. Strip common location suffixes and generic noise (Case Insensitive)
    noise_patterns = [
        r'\bNYC\b', r'\bNew York\b', r'\bNY\b',
        r'\bK-Town\b', r'\bHarlem\b', r'\bSoho\b', r'\bManhattan\b',
        r'\bRestaurant\b', r'\bCafe\b', r'\bBakery\b', r'\bBar\b'
    ]

    clean = name
    for pattern in noise_patterns:
        clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)

    cleaned_result = clean.strip()
    if not cleaned_result and original_name:
        return original_name # Return original name if cleaned result is empty but original was not
    return cleaned_result


def search_place_by_name(query: str, city_context: str = None, max_retries: int = 2) -> Optional[Dict[str, Any]]:
    """
    Geocode a place with strict City/Country validation.
    """
    if not query:
        return None

    headers = {
        "User-Agent": "Plandit-Geocoding-Worker/1.0 (contact@plandit.app)" 
    }
    
    # 1. Base Params
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1  # IMPORTANT: This tells Nominatim to return the city/state/country breakdown
    }

    # 2. Strict Country Limiting (Prevents matches in Saudi Arabia/Ireland/Scotland)
    if TARGET_COUNTRY_CODE:
        params["countrycodes"] = TARGET_COUNTRY_CODE

    for attempt in range(max_retries + 1):
        try:
            print(f"   [API] Query: '{query}' (Context: {city_context}), Attempt: {attempt + 1}")
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                headers=headers,
                params=params,
                timeout=30 # Increased timeout to 30 seconds
            )
            
            if resp.status_code == 429:
                time.sleep(5) 
                continue
            
            if resp.status_code != 200:
                print(f"   [WARN] Nominatim {resp.status_code} for '{query}'")
                return None

            data = resp.json()
            if not data:
                print(f"   [REJECT] No Nominatim result for '{query}'")
                return None

            result = data[0]
            address = result.get("address", {})

            # --- VALIDATION STEP ---
            # If we have a city context (e.g., "New York"), check if the result is actually near there.
            if city_context:
                # Get all address fields that might contain the city name
                found_location = [
                    address.get("city", ""),
                    address.get("town", ""),
                    address.get("village", ""),
                    address.get("county", ""),
                    address.get("state", "") 
                ]
                
                # Check if our target city matches any part of the returned address
                # We use specific string matching to be safe
                is_match = any(city_context.lower() in loc.lower() for loc in found_location)
                
                if not is_match:
                    print(f"   [REJECT] Found '{result.get('display_name')}' but it does not match city '{city_context}'")
                    return None

            return {
                "lat": float(result.get("lat")),
                "lon": float(result.get("lon")),
                "display_name": result.get("display_name"),
                "address": address
            }

        except Exception as e:
            print(f"   [ERR] Nominatim error for '{query}': {e}")
            time.sleep(1)
            
    return None


def geocode_article(url: str, force: bool = False):
    """
    Geocode stops in a specific lemon8 article.
    Only processes if stops_lat or stops_lng are NULL (unless force=True).
    """
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Supabase client not available.")
        return

    # Fetch the article
    try:
        result = (
            supabase.table("lemon8_articles")
            .select("url, itinerary_data, enriched_itinerary_data, stops_lat, stops_lng") 
            .eq("url", url)
            .execute()
        )
        
        if not result.data:
            print(f"ERROR: Article not found: {url}")
            return
        
        article = result.data[0]
        
        # Check if already processed (unless force=True)
        if not force:
            stops_lat_existing = article.get("stops_lat")
            stops_lng_existing = article.get("stops_lng")
            
            # Check if both arrays exist and have at least one coordinate
            is_processed = (
                stops_lat_existing is not None and 
                stops_lng_existing is not None and
                isinstance(stops_lat_existing, list) and
                len(stops_lat_existing) > 0 and 
                len(stops_lng_existing) > 0 and
                stops_lat_existing[0] is not None and
                stops_lng_existing[0] is not None
            )
            
            if is_processed:
                print(f"SKIP: Article already has coordinates ({len(stops_lat_existing)} stops). Use --force to reprocess.")
                return
    except Exception as exc:
        print(f"ERROR: Failed to fetch article: {exc}")
        return

    # Use itinerary_data as the source
    data = article.get("itinerary_data") 
    print(f"[DEBUG] Type of itinerary_data: {type(data)}")
    
    # Handle malformed itinerary_data specifically
    if isinstance(data, list) and all(isinstance(item, str) for item in data) and "city" in data and "stops" in data:
        print(f"WARNING: Malformed itinerary_data (list of keys) for {url[-50:]}: {data}. Skipping article.")
        return
    elif isinstance(data, str):
        try:
            data = json.loads(data)
            print(f"[DEBUG] Successfully parsed string itinerary_data to dict.")
        except json.JSONDecodeError:
            print(f"ERROR: itinerary_data is a malformed JSON string for {url[-50:]}: {data}. Skipping article.")
            return
    
    if not isinstance(data, dict):
        print(f"ERROR: Invalid itinerary_data format (expected dict) for {url[-50:]}: {data}. Skipping article.")
        return

    city = data.get("city") or "New York"  # Default to NYC if missing for context
    stops = data.get("stops")
    if not isinstance(stops, list):
        stops = []

    print(f"Processing {len(stops)} stops for article: {url[-50:]}")
    print(f"City: {city}\n")

    stops_lat: List[Optional[float]] = []
    stops_lng: List[Optional[float]] = []
    updated_stops: List[Dict[str, Any]] = []

    for stop in stops:
        place_name = (stop.get("place_name") or "").strip()

        # --- STRATEGY 1: Cleaned Name + City (Highest Confidence) ---
        clean_name = clean_search_term(place_name)
        query_clean = f"{clean_name}, {city}".strip().strip(",")

        # --- STRATEGY 2: Original Search Query (Fallback) ---
        query_original = (stop.get("search_query") or "").strip()

        # --- STRATEGY 3: Try corrected spellings in search_query first (with location context)
        corrected_queries = []
        if "Ceccinis" in query_original:
            corrected_queries.append(query_original.replace("Ceccinis", "Cecconi's"))
        if "Ceccinis" in place_name:
            # Also try corrected place name with city
            corrected_place = place_name.replace("Ceccinis", "Cecconi's")
            corrected_queries.append(f"{corrected_place}, {city}")
        
        # --- STRATEGY 4: Name variations without location (lower priority)
        name_variations = []
        if "Emmets" in place_name and "Grove" in query_original:
            # Try with apostrophe
            name_variations.append(place_name.replace("Emmets", "Emmet's"))
            # Try Grove Street location as fallback
            name_variations.append("Grove Street West Village New York")

        # --- STRATEGY 5: Raw Place Name (Last Resort) ---
        query_raw = place_name

        result = None
        used_query = None
        # Prioritize queries with location context
        candidates = [query_clean, query_original] + corrected_queries + name_variations + [query_raw]
        for candidate in candidates:
            if not candidate:
                continue
            if len(candidate) < 3:
                continue

            result = search_place_by_name(candidate, city_context=city) # Pass city_context
            used_query = candidate
            if result:
                break

        lat = result["lat"] if result else None
        lng = result["lon"] if result else None

        updated_stop = dict(stop)
        updated_stop["lat"] = lat
        updated_stop["lng"] = lng

        stops_lat.append(lat)
        stops_lng.append(lng)
        updated_stops.append(updated_stop)

        safe_name = place_name.encode('ascii', 'ignore').decode()
        safe_query = (used_query or query_clean or "").encode('ascii', 'ignore').decode()
        if lat:
            print(f"   [OK] {safe_name} -> ({lat:.5f}, {lng:.5f}) [Via: {safe_query}]")
        else:
            safe_query_clean = query_clean.encode('ascii', 'ignore').decode()
            print(f"   [FAIL] {safe_name} | Tried: '{safe_query_clean}'")

        time.sleep(SLEEP_SECONDS)

    if stops:
        updated_data = dict(data)
        updated_data["stops"] = updated_stops

        payload = {
            "enriched_itinerary_data": updated_data, 
            "stops_lat": stops_lat,
            "stops_lng": stops_lng,
        }

        try:
            supabase.table("lemon8_articles").update(payload).eq("url", url).execute()
            print(f"\n--> SAVED article {url[-50:]}...")
            print(f"    Updated {len([s for s in stops_lat if s is not None])}/{len(stops)} stops with coordinates")
        except Exception as exc:
            print(f"ERR: Save failed for {url}: {exc}")


def geocode_unprocessed_articles(limit: int = 100, offset: int = 0):
    """
    Process all articles that haven't been geocoded yet (stops_lat or stops_lng are NULL or empty).
    """
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Supabase client not available.")
        return

    try:
        # Fetch articles that might need geocoding
        # We'll filter client-side since Supabase OR queries for NULL are complex
        result = (
            supabase.table("lemon8_articles")
            .select("url, itinerary_data, enriched_itinerary_data, stops_lat, stops_lng") 
            .not_.is_("itinerary_data", "null") 
            .order("created_at", desc=False)
            .limit(limit * 2)  
            .offset(offset)
            .execute()
        )
        
        all_articles = result.data or []
        
        # Filter to only articles that need geocoding
        articles = []
        for article in all_articles:
            stops_lat = article.get("stops_lat")
            stops_lng = article.get("stops_lng")
            
            # Need geocoding if either is NULL or empty
            needs_geocoding = (
                stops_lat is None or 
                stops_lng is None or
                (isinstance(stops_lat, list) and len(stops_lat) == 0) or
                (isinstance(stops_lng, list) and len(stops_lng) == 0)
            )
            
            if needs_geocoding:
                articles.append(article)
                if len(articles) >= limit:
                    break
        
        print(f"Found {len(articles)} unprocessed articles to geocode\n")
        
        for idx, article in enumerate(articles, 1):
            url = article.get("url")
            print(f"\n[{idx}/{len(articles)}] Processing: {url[-50:]}")
            try:
                geocode_article(url, force=False)
            except Exception as e:
                print(f"ERROR: Failed to process article {url[-50:]}: {e}")
                import traceback
                traceback.print_exc()
            print()  
            
    except Exception as exc:
        print(f"ERROR: Failed to fetch articles: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python geocode_single_article.py <article_url> [--force]")
        print("  python geocode_single_article.py --batch [--limit N] [--offset M]")
        sys.exit(1)
    
    if sys.argv[1] == "--batch":
        limit = 100  # default
        offset = 0   # default
        if "--limit" in sys.argv:
            limit_idx = sys.argv.index("--limit")
            if limit_idx + 1 < len(sys.argv) and sys.argv[limit_idx + 1].isdigit():
                limit = int(sys.argv[limit_idx + 1])
        if "--offset" in sys.argv:
            offset_idx = sys.argv.index("--offset")
            if offset_idx + 1 < len(sys.argv) and sys.argv[offset_idx + 1].isdigit():
                offset = int(sys.argv[offset_idx + 1])
        geocode_unprocessed_articles(limit=limit, offset=offset)
    else:
        url = sys.argv[1]
        force = "--force" in sys.argv or "-f" in sys.argv
        geocode_article(url, force=force)
