"""
Sample geocoder: updates up to 10 rows in each of:
- `yelp_restaurants` (location == null)
- `res_backend_scrapedrestaurant` (latitude/longitude == null)
for records with a non-null address, using google_maps_scraper (no API key).
Intended for quick sanity checks/backfill.

Prereqs:
- Env vars: SUPABASE_URL, SUPABASE_KEY (service role recommended)
- Dependencies: supabase-py, requests (already in requirements), google_maps_scraper module in repo

Usage:
    python backfill_yelp_locations_sample.py
"""

import os
import time
from typing import Dict, Any, List

from supabase_config import get_supabase_client
from google_maps_scraper import search_place_by_name

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))  # rows per table per run
SLEEP_SECONDS = 0.5       # be gentle to avoid blocks


def build_query(row: Dict[str, Any]) -> str:
    """Construct a search string from available fields."""
    parts: List[str] = [
        row.get("name") or "",
        row.get("address") or "",
        row.get("city") or "",
        row.get("state") or "",
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def main():
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Supabase client not available. Set SUPABASE_URL and SUPABASE_KEY.")
        return

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
            print(f"✅ Updated {row.get('name')} -> {loc}")
        else:
            print(f"⚠️  No geocode for yelp_id={row.get('yelp_id')} name={row.get('name')} query='{query}'")

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
            print(f"✅ Updated scraped {row.get('name')} -> {loc}")
        else:
            print(f"⚠️  No geocode for scraped id={row.get('id')} name={row.get('name')} query='{query}'")

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
            print(f"✅ Updated scraped {row.get('name')} -> {loc}")
        else:
            print(f"⚠️  No geocode for scraped id={row.get('id')} name={row.get('name')} query='{query}'")

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()

