"""
Sample geocoder:
- `yelp_restaurants` (location == null)
- `res_backend_scrapedrestaurant` (latitude/longitude == null)
- `lemon8_articles` enriched_itinerary_data stops (geocode search_query)

Uses OpenStreetMap Nominatim (Free, requires polite usage).
"""

import os
import time
import re
from typing import Dict, Any, List, Optional

import requests
from supabase_config import get_supabase_client

# --- Configuration ---
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "1.1"))  # Critical for Nominatim
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "").strip()
LEMON8_LIMIT = int(os.getenv("LEMON8_LIMIT", "100"))


def clean_search_term(name: str) -> str:
    """
    Aggressive cleaning to fix 'HOJOKBAN NYC', 'Lido Harlem Restaurant', 'Hani's +'.
    Removes specific noise words that confuse strict geocoders.
    """
    if not name:
        return ""

    # 1. Remove special separators and replace with space
    # Matches |, +, -, :, and multiple spaces
    name = re.sub(r'[|+\-:]', ' ', name)

    # 2. Strip common location suffixes and generic noise (Case Insensitive)
    # Be careful not to strip words that might be the *actual* name (like "New York Pizza")
    # providing they appear at the end or as distinct tokens.
    noise_patterns = [
        r'\bNYC\b', r'\bNew York\b', r'\bNY\b',
        r'\bK-Town\b', r'\bHarlem\b', r'\bSoho\b', r'\bManhattan\b',
        r'\bRestaurant\b', r'\bCafe\b', r'\bBakery\b', r'\bBar\b'
    ]

    clean = name
    for pattern in noise_patterns:
        clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)

    return clean.strip()


def build_query(row: Dict[str, Any]) -> str:
    """Construct a search string for Yelp/Scraped tables."""
    parts: List[str] = [
        row.get("name") or "",
        row.get("address") or "",
        row.get("city") or "",
        row.get("state") or "",
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def search_place_by_name(query: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
    """
    Geocode a place using OpenStreetMap Nominatim.
    """
    if not query:
        return None

    headers = {
        "User-Agent": f"res-geocode/1.0 ({NOMINATIM_EMAIL})" if NOMINATIM_EMAIL else "res-geocode/1.0"
    }
    params = {"q": query, "format": "json", "limit": 1}

    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                headers=headers,
                params=params,
                timeout=15,
            )
            if resp.status_code != 200:
                print(f"WARN: Nominatim {resp.status_code} for '{query}'")
                if resp.status_code == 429:  # Rate limit hit
                    time.sleep(5)
                continue

            data = resp.json()
            if not data:
                return None

            top = data[0]
            return {
                "lat": float(top.get("lat")),
                "lon": float(top.get("lon")),
                "display_name": top.get("display_name"),
            }
        except Exception as exc:
            print(f"WARN: Nominatim error for '{query}': {exc}")
            time.sleep(1.0)
    return None


def geocode_lemon8_articles(limit: int = LEMON8_LIMIT):
    """
    Geocode stops in lemon8_articles using robust fallback logic.
    """
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Supabase client not available.")
        return

    articles = (
        supabase.table("lemon8_articles")
        .select("url, enriched_itinerary_data")
        .not_.is_("enriched_itinerary_data", "null")
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
        .data
    )

    print(f"Fetched {len(articles)} lemon8 articles for geocoding")

    for article in articles:
        url = article.get("url")
        # Handle data structure variants (list vs dict)
        raw_data = article.get("enriched_itinerary_data")
        if isinstance(raw_data, list) and raw_data:
            data = raw_data[0]
        elif isinstance(raw_data, dict):
            data = raw_data
        else:
            data = {}

        city = data.get("city") or "New York"  # Default to NYC if missing for context
        stops = data.get("stops")
        if not isinstance(stops, list):
            stops = []

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

            # --- STRATEGY 3: Raw Place Name (Last Resort) ---
            query_raw = place_name

            result = None
            used_query = None
            for candidate in [query_clean, query_original, query_raw]:
                if not candidate:
                    continue
                if len(candidate) < 3:
                    continue

                result = search_place_by_name(candidate)
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
            if lat:
                print(f"   [OK] {safe_name} -> ({lat:.5f}, {lng:.5f}) [Via: {used_query}]")
            else:
                print(f"   [FAIL] {safe_name} | Tried: '{query_clean}'")

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
                print(f"--> SAVED article {url[-20:]}...")
            except Exception as exc:
                print(f"ERR: Save failed for {url}: {exc}")


def main():
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Supabase client not available. Set SUPABASE_URL and SUPABASE_KEY.")
        return

    # 1. Run Lemon8 Geocoder
    geocode_lemon8_articles()

    # 2. Run Yelp Geocoder
    rows = (
        supabase.table("yelp_restaurants")
        .select("yelp_id,name,address,city,state")
        .is_("location", "null")
        .not_.is_("address", "null")
        .limit(BATCH_SIZE)
        .execute()
        .data
    )
    print(f"\nFetched {len(rows)} Yelp rows needing geocode")
    for row in rows:
        query = build_query(row)
        info = search_place_by_name(query)

        if info:
            loc = {"lat": info["lat"], "lng": info["lon"]}
            supabase.table("yelp_restaurants").update({"location": loc}).eq("yelp_id", row["yelp_id"]).execute()
            print(f"   [YELP] Updated {row.get('name')}")
        else:
            print(f"   [YELP] Failed {row.get('name')}")
        time.sleep(SLEEP_SECONDS)

    # 3. Run Scraped Restaurants Geocoder
    scraped_rows = (
        supabase.table("res_backend_scrapedrestaurant")
        .select("id,name,address,street_address,city,state")
        .is_("latitude", "null")
        .not_.is_("address", "null")
        .eq("is_active", True)
        .is_("duplicate_of_id", "null")
        .limit(BATCH_SIZE)
        .execute()
        .data
    )
    print(f"\nFetched {len(scraped_rows)} Scraped rows needing geocode")
    for row in scraped_rows:
        parts = [
            row.get("name"),
            row.get("street_address"),
            row.get("city"),
            row.get("state")
        ]
        query = " ".join([p.strip() for p in parts if p and p.strip()])

        info = search_place_by_name(query)
        if info:
            loc = {"latitude": info["lat"], "longitude": info["lon"]}
            supabase.table("res_backend_scrapedrestaurant").update(loc).eq("id", row["id"]).execute()
            print(f"   [SCRAPED] Updated {row.get('name')}")
        else:
            print(f"   [SCRAPED] Failed {row.get('name')}")
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
