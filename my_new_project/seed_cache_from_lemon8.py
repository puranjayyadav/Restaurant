"""
Seed geohash cache from lemon8_articles stops coordinates.
Pulls stop lat/lng arrays and calls get_cached_or_scraped_places to
populate ScrapedPlaceCache.
"""

import os
import sys
import itertools
from datetime import datetime

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_new_project.settings")

# Ensure project root and workspace root on path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.dirname(BASE_DIR)
PROJECT_PACKAGE_DIR = os.path.join(BASE_DIR, "my_new_project")

# Add workspace root and inner package directory
for path in (WORKSPACE_ROOT, PROJECT_PACKAGE_DIR, BASE_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import django

django.setup()

from supabase_config import get_supabase_client
from res_backend.scraping_service import get_cached_or_scraped_places


def main(max_rows: int = 50) -> None:
    supabase = get_supabase_client()
    if not supabase:
        print("ERROR: No Supabase client (check supabase_config).")
        return

    print(f"[{datetime.utcnow().isoformat()}] Fetching lemon8_articles with coords...")
    res = (
        supabase.table("lemon8_articles")
        .select("stops_lat, stops_lng")
        .not_.is_("stops_lat", "null")
        .execute()
    )
    rows = res.data or []
    print(f"Fetched {len(rows)} rows")

    seeded = 0
    for row in rows[:max_rows]:
        lats = row.get("stops_lat") or []
        lngs = row.get("stops_lng") or []
        for lat, lng in itertools.islice(zip(lats, lngs), 0, None):
            if lat is None or lng is None:
                continue
            latf = float(lat)
            lngf = float(lng)
            places, cache_hit = get_cached_or_scraped_places(
                lat=latf,
                lon=lngf,
                query=None,
                use_time_context=True,
                radius_km=1.0,
            )
            seeded += 1
            print(
                f"Seeded ({latf:.5f}, {lngf:.5f}) -> {len(places)} places; cache_hit={cache_hit}"
            )
    print(f"Done. Seeded {seeded} stop coordinates.")


if __name__ == "__main__":
    main()

