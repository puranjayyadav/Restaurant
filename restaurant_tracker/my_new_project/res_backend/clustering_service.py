"""
Clustering and variety scoring for walkable neighborhoods.

Uses DBSCAN with Haversine distance to find walkable clusters and
Shannon entropy to score category variety. Supports optional gap
filling using the existing google_maps_scraper (no official API).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import math

import numpy as np
from sklearn.cluster import DBSCAN
from scipy.stats import entropy

from .utils import haversine_distance


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_place_data(
    places: List[Dict[str, Any]],
    user_location: Optional[Tuple[float, float]] = None,
    max_distance_km: float = 100.0,
) -> List[Dict[str, Any]]:
    """
    Basic hygiene pass:
    - Drop places without coordinates
    - Optionally drop extreme outliers far from the user (e.g., Dublin glitch)
    """
    cleaned: List[Dict[str, Any]] = []

    for place in places:
        lat = (
            place.get("lat")
            or place.get("latitude")
            or place.get("geometry", {})
            .get("location", {})
            .get("lat")
        )
        lng = (
            place.get("long")
            or place.get("lng")
            or place.get("longitude")
            or place.get("geometry", {})
            .get("location", {})
            .get("lng")
        )

        lat_f = _safe_float(lat)
        lng_f = _safe_float(lng)
        if lat_f is None or lng_f is None:
            # No usable coordinates – skip for clustering
            continue

        if user_location:
            d_m = haversine_distance(
                user_location[0], user_location[1], lat_f, lng_f
            )
            if d_m / 1000.0 > max_distance_km:
                # Extreme outlier relative to user – likely bad geocode
                continue

        # Normalize coordinates so downstream code can rely on lat/lng keys
        place = dict(place)
        place["lat"] = lat_f
        place["lng"] = lng_f
        cleaned.append(place)

    return cleaned


def cluster_places(
    places: List[Dict[str, Any]],
    eps_km: float = 0.4,
    min_samples: int = 3,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Run DBSCAN using Haversine distance on lat/lng coordinates.

    Returns:
        labels: Cluster label for each place (-1 = noise)
        coords_rad: Coordinates in radians (N x 2)
    """
    if not places:
        return np.array([]), np.zeros((0, 2))

    coords = np.array([[p["lat"], p["lng"]] for p in places], dtype=float)
    # Convert to radians for Haversine
    coords_rad = np.radians(coords)

    kilometers_per_radian = 6371.0088
    eps_rad = eps_km / kilometers_per_radian

    db = DBSCAN(
        eps=eps_rad,
        min_samples=min_samples,
        metric="haversine",
    )
    labels = db.fit_predict(coords_rad)
    return labels, coords_rad


def _extract_category(place: Dict[str, Any]) -> Optional[str]:
    """
    Get the best available category label for variety scoring.
    Preference order:
    - solver_data.category_normalized
    - explicit 'category' field
    - first Google Places 'types' entry
    """
    solver_data = place.get("solver_data") or {}
    cat_norm = solver_data.get("category_normalized")
    if isinstance(cat_norm, str) and cat_norm.strip():
        return cat_norm.strip()

    direct_cat = place.get("category")
    if isinstance(direct_cat, str) and direct_cat.strip():
        return direct_cat.strip()

    types = place.get("types") or []
    if types:
        return str(types[0]).strip()

    return None


def calculate_shannon_entropy(categories: List[str]) -> float:
    """
    Shannon entropy over category labels.
    """
    if not categories:
        return 0.0
    values, counts = np.unique(categories, return_counts=True)
    probs = counts / counts.sum()
    return float(entropy(probs))


def score_cluster_variety(
    cluster_places: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compute variety score and basic stats for a cluster.
    """
    cats: List[str] = []
    for p in cluster_places:
        cat = _extract_category(p)
        if cat:
            cats.append(cat)

    var_score = calculate_shannon_entropy(cats)
    size = len(cluster_places)
    unique_cats = sorted(set(cats)) if cats else []

    # Slightly favor larger clusters
    composite_score = var_score * (1.0 + math.log1p(size))

    # Compute simple geometric center
    if size > 0:
        lats = [p["lat"] for p in cluster_places]
        lngs = [p["lng"] for p in cluster_places]
        center = (float(sum(lats) / size), float(sum(lngs) / size))
    else:
        center = (0.0, 0.0)

    return {
        "variety_score": var_score,
        "size": size,
        "unique_categories": unique_cats,
        "composite_score": composite_score,
        "center": center,
    }


def _map_category_to_vertical(cat: str) -> str:
    """
    Map normalized categories into coarse verticals:
    Eat, Drink, Activity, Relax.
    """
    c = cat.lower()
    eat_keywords = [
        "food",
        "restaurant",
        "brunch",
        "lunch",
        "dinner",
        "bakery",
        "dessert",
        "pizza",
    ]
    drink_keywords = ["bar", "cocktail", "wine", "brew", "pub"]
    relax_keywords = ["park", "spa", "garden"]
    activity_keywords = [
        "museum",
        "gallery",
        "shop",
        "shopping",
        "activity",
        "music",
        "nightlife",
    ]

    for k in eat_keywords:
        if k in c:
            return "Eat"
    for k in drink_keywords:
        if k in c:
            return "Drink"
    for k in relax_keywords:
        if k in c:
            return "Relax"
    for k in activity_keywords:
        if k in c:
            return "Activity"
    return "Activity"


def identify_missing_categories(
    cluster: List[Dict[str, Any]],
    required_verticals: List[str],
) -> List[str]:
    """
    Determine which meta-verticals are missing from the cluster.
    """
    present: set = set()
    for p in cluster:
        cat = _extract_category(p)
        if not cat:
            continue
        v = _map_category_to_vertical(cat)
        present.add(v)

    missing = [v for v in required_verticals if v not in present]
    return missing


def _ensure_scraper_import():
    """
    Import google_maps_scraper from project root, adjusting sys.path if needed.
    """
    import os
    import sys

    try:
        import google_maps_scraper  # type: ignore
        return google_maps_scraper
    except ImportError:
        # Add workspace root to path (three levels up from this file)
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        import google_maps_scraper  # type: ignore

        return google_maps_scraper


def augment_cluster_with_category(
    cluster_center: Tuple[float, float],
    missing_category: str,
    radius_m: float = 500.0,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Use the existing google_maps_scraper to fetch candidate places
    for a missing category near the cluster center.
    """
    try:
        google_maps_scraper = _ensure_scraper_import()
    except Exception as e:
        print(f"DEBUG: Failed to import google_maps_scraper: {e}")
        return []

    lat, lng = cluster_center

    # Simple mapping from meta-vertical / normalized category to search query
    cat_lower = missing_category.lower()
    if cat_lower == "eat":
        query = "restaurant"
    elif cat_lower == "drink":
        query = "bar"
    elif cat_lower == "relax":
        query = "park"
    else:  # Activity
        query = "museum OR park OR things to do"

    try:
        scraped = google_maps_scraper.get_google_maps_data(
            query=query,
            lat=lat,
            lon=lng,
            count=max_results,
        )
    except Exception as e:
        print(f"DEBUG: google_maps_scraper.get_google_maps_data failed: {e}")
        return []

    enriched: List[Dict[str, Any]] = []
    for place in scraped or []:
        p_lat = _safe_float(place.get("lat"))
        p_lng = _safe_float(place.get("long") or place.get("lng"))
        if p_lat is None or p_lng is None:
            continue

        d_m = haversine_distance(lat, lng, p_lat, p_lng)
        if d_m > radius_m:
            continue

        # Normalize to the same shape used elsewhere (lat/lng keys)
        norm_place = dict(place)
        norm_place["lat"] = p_lat
        norm_place["lng"] = p_lng
        enriched.append(norm_place)

    return enriched


def find_walkable_neighborhoods(
    places: List[Dict[str, Any]],
    user_location: Tuple[float, float],
    enable_gap_filling: bool = True,
    top_k: int = 3,
    required_verticals: Optional[List[str]] = None,
    eps_km: float = 0.4,
    min_samples: int = 3,
) -> List[Dict[str, Any]]:
    """
    Main entrypoint:
    - Clean inputs
    - DBSCAN cluster
    - Score clusters by variety and size
    - Optionally gap-fill only the top_k candidates, then re-score

    Returns:
        List of cluster dicts sorted by composite_score desc:
        {
          "label": int,
          "places": [...],
          "variety_score": float,
          "size": int,
          "unique_categories": [...],
          "composite_score": float,
          "center": (lat, lng),
          "meta_verticals": [...],
        }
    """
    if required_verticals is None:
        required_verticals = ["Eat", "Drink", "Activity", "Relax"]

    cleaned = clean_place_data(places, user_location=user_location)
    if not cleaned:
        return []

    labels, _ = cluster_places(cleaned, eps_km=eps_km, min_samples=min_samples)
    if labels.size == 0:
        return []

    # Group by label (ignore noise = -1)
    clusters_map: Dict[int, List[Dict[str, Any]]] = {}
    for place, label in zip(cleaned, labels):
        if label == -1:
            continue
        clusters_map.setdefault(int(label), []).append(place)

    clusters: List[Dict[str, Any]] = []
    for label, c_places in clusters_map.items():
        if not c_places:
            continue
        stats = score_cluster_variety(c_places)
        meta_verticals = set()
        for p in c_places:
            cat = _extract_category(p)
            if not cat:
                continue
            meta_verticals.add(_map_category_to_vertical(cat))

        cluster_obj = {
            "label": label,
            "places": c_places,
            "variety_score": stats["variety_score"],
            "size": stats["size"],
            "unique_categories": stats["unique_categories"],
            "composite_score": stats["composite_score"],
            "center": stats["center"],
            "meta_verticals": sorted(meta_verticals),
        }
        clusters.append(cluster_obj)

    if not clusters:
        return []

    # Rank by composite_score first, then size
    clusters.sort(
        key=lambda c: (c.get("composite_score", 0.0), c.get("size", 0)),
        reverse=True,
    )

    if not enable_gap_filling:
        return clusters

    # Lazy gap filling – only for top_k candidates
    top_candidates = clusters[: max(1, top_k)]
    augmented_clusters: List[Dict[str, Any]] = []

    for cluster in top_candidates:
        center = cluster["center"]
        current_places = list(cluster["places"])
        missing = identify_missing_categories(current_places, required_verticals)

        added_places: List[Dict[str, Any]] = []
        for vertical in missing:
            new_places = augment_cluster_with_category(center, vertical)
            for np_ in new_places:
                # Deduplicate by place_id + coordinates
                existing_ids = {
                    p.get("place_id") for p in current_places if p.get("place_id")
                }
                if np_.get("place_id") and np_["place_id"] in existing_ids:
                    continue
                added_places.append(np_)

        if added_places:
            current_places = current_places + added_places

        stats = score_cluster_variety(current_places)
        meta_verticals = set()
        for p in current_places:
            cat = _extract_category(p)
            if not cat:
                continue
            meta_verticals.add(_map_category_to_vertical(cat))

        augmented_clusters.append(
            {
                "label": cluster["label"],
                "places": current_places,
                "variety_score": stats["variety_score"],
                "size": stats["size"],
                "unique_categories": stats["unique_categories"],
                "composite_score": stats["composite_score"],
                "center": stats["center"],
                "meta_verticals": sorted(meta_verticals),
                "gap_filled": bool(added_places),
            }
        )

    # Keep any non-top clusters as-is (no gap fill)
    remaining = clusters[len(top_candidates) :]
    all_clusters = augmented_clusters + remaining
    all_clusters.sort(
        key=lambda c: (c.get("composite_score", 0.0), c.get("size", 0)),
        reverse=True,
    )
    return all_clusters


