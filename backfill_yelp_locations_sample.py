"""
Sample geocoder:
- `yelp_restaurants` (location == null)
- `res_backend_scrapedrestaurant` (latitude/longitude == null)
- NEW: first 3 `lemon8_articles` enriched_itinerary_data stops (geocode search_query)
for records with a non-null address, using OpenStreetMap Nominatim (no API key).
Intended for quick sanity checks/backfill.

Prereqs:
- Env vars: SUPABASE_URL, SUPABASE_KEY (service role recommended)
- Dependencies: supabase-py, requests (already in requirements), google_maps_scraper module in repo

Usage:
    python backfill_yelp_locations_sample.py
"""

import os
import time
from typing import Dict, Any, List, Optional

import requests
from supabase_config import get_supabase_client

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))  # rows per table per run
SLEEP_SECONDS = float(os.getenv("SLEEP_SECONDS", "1.1"))  # respect Nominatim 1s throttle
NOMINATIM_EMAIL = os.getenv("NOMINATIM_EMAIL", "").strip()  # optional, polite UA
LEMON8_LIMIT = int(os.getenv("LEMON8_LIMIT", "100"))


def build_query(row: Dict[str, Any]) -> str:
    """Construct a search string from available fields."""
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

    Returns dict with lat, lon, display_name or None.
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
    Geocode stops in lemon8_articles.enriched_itinerary_data for the first `limit` rows.
    Stores lat/lng arrays in separate columns (stops_lat, stops_lng) and also injects
    lat/lng into each stop inside enriched_itinerary_data.
    """
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Supabase client not available. Set SUPABASE_URL and SUPABASE_KEY.")
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
        raw_data = article.get("enriched_itinerary_data") or {}
        if isinstance(raw_data, list):
            data = raw_data[0] if raw_data and isinstance(raw_data[0], dict) else {}
        elif isinstance(raw_data, dict):
            data = raw_data
        else:
            data = {}

        city = data.get("city") or ""
        stops = data.get("stops") or []
        if not isinstance(stops, list):
            stops = []

        stops_lat: List[Optional[float]] = []
        stops_lng: List[Optional[float]] = []
        updated_stops: List[Dict[str, Any]] = []

        for stop in stops:
            place_name = (stop.get("place_name") or "").strip()
            # Primary: clean "Name, City" (strip symbols that hurt matching)
            clean_name = place_name.replace("+", " ").replace("|", " ").strip()
            simple_query = f"{clean_name}, {city}".strip().strip(",")

            # Secondary: original search_query if present
            noisy_query = (stop.get("search_query") or "").strip()

            # Tertiary: just place name
            fallback_query = place_name

            result = None
            for candidate in [simple_query, noisy_query, fallback_query]:
                if candidate:
                    result = search_place_by_name(candidate)
                if result and result.get("lat") and result.get("lon"):
                    break

            lat = float(result["lat"]) if result and result.get("lat") else None
            lng = float(result["lon"]) if result and result.get("lon") else None

            updated_stop = dict(stop)
            updated_stop["lat"] = lat
            updated_stop["lng"] = lng

            stops_lat.append(lat)
            stops_lng.append(lng)
            updated_stops.append(updated_stop)

            if lat and lng:
                print(f"OK: {stop.get('place_name')} -> ({lat}, {lng})")
            else:
                print(f"WARN: No geocode for '{simple_query}'")

            time.sleep(SLEEP_SECONDS)

        updated_data = dict(data)
        updated_data["stops"] = updated_stops

        payload = {
            "enriched_itinerary_data": updated_data,
            "stops_lat": stops_lat,
            "stops_lng": stops_lng,
        }

        try:
            supabase.table("lemon8_articles").update(payload).eq("url", url).execute()
            print(f"UPDATED article {url} with {len(updated_stops)} stops")
        except Exception as exc:
            print(f"WARN: Failed to update stops_lat/stops_lng for {url}: {exc}")
            # Fallback: at least persist enriched_itinerary_data with lat/lng inside stops
            try:
                supabase.table("lemon8_articles").update(
                    {"enriched_itinerary_data": updated_data}
                ).eq("url", url).execute()
                print(f"UPDATED enriched_itinerary_data only for {url}")
            except Exception as exc2:
                print(f"ERROR: Failed to update article {url}: {exc2}")


def main():
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: Supabase client not available. Set SUPABASE_URL and SUPABASE_KEY.")
        return

    # Geocode enriched itineraries (default via env LEMON8_LIMIT, default 100)
    geocode_lemon8_articles()

    rows = (
        supabase.table("yelp_restaurants")
        .select("yelp_id,name,address,city,state")
        .is_("location", "null")
        .not_.is_("address", "null")
        .limit(BATCH_SIZE)
        .execute()
        .data
    )

    print(f"Fetched {len(rows)} rows needing geocode")

    for row in rows:
        query = build_query(row)
        if not query:
            print(f"Skipping id={row.get('id')} (no query fields)")
            continue

        info = search_place_by_name(query)
        if info and info.get("lat") and info.get("lon"):
            loc = {"lat": float(info["lat"]), "lng": float(info["lon"])}
            supabase.table("yelp_restaurants").update({"location": loc}).eq("yelp_id", row["yelp_id"]).execute()
            print(f"OK: Updated {row.get('name')} -> {loc}")
        else:
            print(f"WARN: No geocode for yelp_id={row.get('yelp_id')} name={row.get('name')} query='{query}'")

        time.sleep(SLEEP_SECONDS)

    # ---------- res_backend_scrapedrestaurant ----------
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

    print(f"Fetched {len(scraped_rows)} scraped rows needing geocode")

    for row in scraped_rows:
        parts: List[str] = [
            row.get("name") or "",
            row.get("street_address") or "",
            row.get("address") or "",
            row.get("city") or "",
            row.get("state") or "",
        ]
        query = " ".join(p.strip() for p in parts if p and p.strip())

        if not query:
            print(f"Skipping scraped id={row.get('id')} (no query fields)")
            continue

        info = search_place_by_name(query)
        if info and info.get("lat") and info.get("lon"):
            loc = {"latitude": float(info["lat"]), "longitude": float(info["lon"])}
            supabase.table("res_backend_scrapedrestaurant").update(loc).eq("id", row["id"]).execute()
            print(f"OK: Updated scraped {row.get('name')} -> {loc}")
        else:
            print(f"WARN: No geocode for scraped id={row.get('id')} name={row.get('name')} query='{query}'")

        time.sleep(SLEEP_SECONDS)

    # ---------- res_backend_scrapedrestaurant ----------
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

    print(f"Fetched {len(scraped_rows)} scraped rows needing geocode")

    for row in scraped_rows:
        parts: List[str] = [
            row.get("name") or "",
            row.get("street_address") or "",
            row.get("address") or "",
            row.get("city") or "",
            row.get("state") or "",
        ]
        query = " ".join(p.strip() for p in parts if p and p.strip())

        if not query:
            print(f"Skipping scraped id={row.get('id')} (no query fields)")
            continue

        info = search_place_by_name(query)
        if info and info.get("lat") and info.get("lon"):
            loc = {"latitude": float(info["lat"]), "longitude": float(info["lon"])}
            supabase.table("res_backend_scrapedrestaurant").update(loc).eq("id", row["id"]).execute()
            print(f"OK: Updated scraped {row.get('name')} -> {loc}")
        else:
            print(f"WARN: No geocode for scraped id={row.get('id')} name={row.get('name')} query='{query}'")

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()

