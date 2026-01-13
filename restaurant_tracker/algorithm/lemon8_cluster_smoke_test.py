"""
Smoke test: cluster Lemon8 itinerary stops from Supabase.

Fetches a small sample from lemon8_articles.enriched_itinerary_data,
extracts stops (with solver_data), runs find_walkable_neighborhoods,
and prints a JSON summary of the top clusters.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Tuple


def _safe_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _normalize_enriched_itinerary(raw: Any) -> Dict[str, Any]:
    """
    Handle both list and dict forms of enriched_itinerary_data.
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, dict):
            return first
    return {}


def _build_places_from_articles(articles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Tuple[float, float] | None]:
    places: List[Dict[str, Any]] = []
    lat_acc: List[float] = []
    lng_acc: List[float] = []

    for article in articles:
        url = article.get("url") or ""
        enriched_raw = article.get("enriched_itinerary_data")
        data = _normalize_enriched_itinerary(enriched_raw)
        stops = data.get("stops") or []
        if not isinstance(stops, list):
            continue

        for idx, stop in enumerate(stops):
            if not isinstance(stop, dict):
                continue
            lat = _safe_float(stop.get("lat"))
            lng = _safe_float(stop.get("lng"))
            if lat is None or lng is None:
                continue

            place = {
                "place_id": f"{url}::{idx}",
                "name": stop.get("place_name") or stop.get("name") or f"Stop {idx+1}",
                "lat": lat,
                "lng": lng,
                "category": stop.get("category"),
                "solver_data": stop.get("solver_data") or {},
            }
            places.append(place)
            lat_acc.append(lat)
            lng_acc.append(lng)

    if not places or not lat_acc:
        return places, None

    center = (sum(lat_acc) / len(lat_acc), sum(lng_acc) / len(lng_acc))
    return places, center


def main() -> None:
    # Ensure project root is on sys.path
    root = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(root)
    my_new_project_dir = os.path.join(project_root, "my_new_project")
    
    # Add both project root and my_new_project to path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if my_new_project_dir not in sys.path:
        sys.path.insert(0, my_new_project_dir)
    
    # Change to my_new_project directory (like manage.py does)
    original_cwd = os.getcwd()
    try:
        os.chdir(my_new_project_dir)
        
        # Configure Django settings so res_backend imports work
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_new_project.settings")
        import django  # type: ignore

        django.setup()
    except Exception as e:  # pragma: no cover - diagnostic only
        print(json.dumps({"status": "error", "stage": "django_setup", "error": str(e)}))
        return
    finally:
        os.chdir(original_cwd)

    try:
        from supabase_config import get_supabase_client
        from res_backend.clustering_service import find_walkable_neighborhoods
    except Exception as e:  # pragma: no cover - diagnostic only
        print(json.dumps({"status": "error", "stage": "import", "error": str(e)}))
        return

    supabase = get_supabase_client()
    if not supabase:
        print(json.dumps({"status": "error", "stage": "supabase", "error": "NO_SUPABASE_CLIENT"}))
        return

    try:
        res = (
            supabase.table("lemon8_articles")
            .select("url,enriched_itinerary_data")
            .not_.is_("enriched_itinerary_data", "null")
            .execute()
        )
        articles: List[Dict[str, Any]] = res.data or []
    except Exception as e:  # pragma: no cover - diagnostic only
        print(json.dumps({"status": "error", "stage": "query", "error": str(e)}))
        return

    places, center = _build_places_from_articles(articles)

    # Debug: show which places were built from the fetched articles
    try:
        print(
            json.dumps(
                {
                    "status": "debug_places",
                    "place_count": len(places),
                    "places": places,
                },
                indent=2,
            )
        )
    except Exception:
        # Fallback if something inside places isn't JSON-serializable
        print(
            json.dumps(
                {
                    "status": "debug_places",
                    "place_count": len(places),
                }
            )
        )

    if not places:
        print(json.dumps({"status": "ok", "message": "NO_STOPS_WITH_COORDS"}))
        return

    # Use centroid of stops as pseudo user_location
    if center is None:
        # Fallback to Manhattan-ish center
        center = (40.7306, -73.9352)

    clusters = find_walkable_neighborhoods(
        places,
        user_location=center,
        enable_gap_filling=True,
        top_k=3,
        eps_km=1.0,  # expanded radius: 1km instead of 0.4km
        min_samples=3,
    )

    summary = [
        {
            "label": c.get("label"),
            "size": c.get("size"),
            "variety_score": round(float(c.get("variety_score", 0.0)), 4),
            "composite_score": round(float(c.get("composite_score", 0.0)), 4),
            "unique_categories": c.get("unique_categories", []),
            "meta_verticals": c.get("meta_verticals", []),
            "gap_filled": c.get("gap_filled", False),
        }
        for c in (clusters[:3] if clusters else [])
    ]

    print(
        json.dumps(
            {
                "status": "ok",
                "article_count": len(articles),
                "place_count": len(places),
                "cluster_count": len(clusters),
                "top_clusters": summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


