"""
End-to-end test suite for critical itinerary APIs.

Endpoints covered:
- POST /api/api/parse-query/
- POST /api/api/geocode-location/
- POST /api/api/generate-itinerary/
- POST /api/api/itinerary-details/

Run: python test_api_end_to_end.py
You can override BASE_URL via the BASE_URL env var.
"""

import os
import time
import math
from typing import Any, Dict, List, Optional, Tuple

import requests

# CONFIG
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ENDPOINTS = {
    "parse_query": f"{BASE_URL}/api/api/parse-query/",
    "geocode_location": f"{BASE_URL}/api/api/geocode-location/",
    "generate_itinerary": f"{BASE_URL}/api/api/generate-itinerary/",
    "itinerary_details": f"{BASE_URL}/api/api/itinerary-details/",
}

TIMEOUTS = {
    "parse_query": 30,
    "geocode_location": 20,
    "generate_itinerary": 180,
    "itinerary_details": 60,
}

NYC_BOUNDS = {
    "min_lat": 40.4774,
    "max_lat": 40.9176,
    "min_lon": -74.2591,
    "max_lon": -73.7004,
}

# COLORS
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


def print_result(success: bool, message: str) -> None:
    color = GREEN if success else RED
    print(f"{color}{'[PASS]' if success else '[FAIL]'}{RESET} {message}")


def print_section(title: str) -> None:
    print(f"\n{MAGENTA}{'=' * 72}{RESET}")
    print(f"{MAGENTA}{title}{RESET}")
    print(f"{MAGENTA}{'=' * 72}{RESET}")


def print_kv(title: str, items: List[Tuple[str, str]]) -> None:
    print(f"{BLUE}{title}{RESET}")
    for key, value in items:
        print(f"  - {key}: {value}")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def in_nyc_bounds(lat: float, lon: float) -> bool:
    return NYC_BOUNDS["min_lat"] <= lat <= NYC_BOUNDS["max_lat"] and NYC_BOUNDS["min_lon"] <= lon <= NYC_BOUNDS["max_lon"]


def post_json(name: str, endpoint: str, payload: Dict[str, Any], timeout: int) -> Optional[Dict[str, Any]]:
    """POST helper with consistent logging."""
    print(f"\n{CYAN}Calling {name}{RESET} -> {endpoint}")
    print_kv("Request", [("payload", str(payload))])
    start = time.time()
    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        duration = time.time() - start
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            print_result(False, f"{name} HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        print_kv("Response", [("time", f"{duration:.2f}s"), ("keys", ", ".join(sorted(data.keys())) if isinstance(data, dict) else "list")])
        return data
    except requests.exceptions.ConnectionError:
        print_result(False, f"{name} failed: could not connect to {endpoint}")
    except requests.exceptions.Timeout:
        print_result(False, f"{name} timed out after {timeout}s")
    except Exception as exc:
        print_result(False, f"{name} unexpected error: {exc}")
    return None


# --- Individual endpoint tests ---
def test_geocode_returns_valid_coords() -> bool:
    payload = {"location_hint": "soho"}
    data = post_json("Geocode basic", ENDPOINTS["geocode_location"], payload, TIMEOUTS["geocode_location"])
    if not data:
        return False

    try:
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
    except (TypeError, ValueError):
        print_result(False, f"Geocode returned invalid lat/lon: {data}")
        return False

    if not in_nyc_bounds(lat, lon):
        print_result(False, f"Coordinates out of NYC bounds: ({lat}, {lon})")
        return False

    print_result(True, f"Coordinates within NYC bounds: ({lat:.4f}, {lon:.4f})")
    return True


def test_geocode_randomization_varies() -> bool:
    payload = {"location_hint": "soho"}
    first = post_json("Geocode randomization (1)", ENDPOINTS["geocode_location"], payload, TIMEOUTS["geocode_location"])
    second = post_json("Geocode randomization (2)", ENDPOINTS["geocode_location"], payload, TIMEOUTS["geocode_location"])
    if not first or not second:
        return False

    try:
        lat1, lon1 = float(first["latitude"]), float(first["longitude"])
        lat2, lon2 = float(second["latitude"]), float(second["longitude"])
    except Exception:
        print_result(False, f"Could not parse coordinates: {first} {second}")
        return False

    distance_m = haversine_km(lat1, lon1, lat2, lon2) * 1000
    # Expect variety; offset is 500m-2km so allow small tolerance.
    if distance_m < 50:
        print_result(False, f"Coordinates too similar ({distance_m:.1f}m apart) - randomization may be off")
        return False

    print_result(True, f"Randomization produced distinct points ({distance_m:.1f}m apart)")
    return True


def test_geocode_requires_hint() -> bool:
    print(f"\n{CYAN}Calling Geocode validation{RESET} -> {ENDPOINTS['geocode_location']}")
    try:
        resp = requests.post(ENDPOINTS["geocode_location"], json={}, timeout=TIMEOUTS["geocode_location"])
        if resp.status_code == 400:
            print_result(True, "Missing location_hint returns 400")
            return True
        print_result(False, f"Expected 400 for missing location_hint, got {resp.status_code}")
        return False
    except requests.exceptions.ConnectionError:
        print_result(False, "Geocode validation failed: could not connect to server")
        return False
    except requests.exceptions.Timeout:
        print_result(False, "Geocode validation timed out")
        return False


def test_parse_query_maps_fields() -> bool:
    payload = {"query": "romantic indian places in soho"}
    data = post_json("Parse query", ENDPOINTS["parse_query"], payload, TIMEOUTS["parse_query"])
    if not data:
        return False

    required_keys = ["selected_vibe", "cuisine_preferences", "social_context", "location_hint"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        print_result(False, f"Parse response missing keys: {missing}")
        return False

    if not data.get("cuisine_preferences"):
        print_result(False, "Parse response did not return cuisine_preferences")
        return False

    print_result(True, f"Parse extracted vibe={data.get('selected_vibe')}, location={data.get('location_hint')}, cuisines={len(data.get('cuisine_preferences', []))}")
    return True


def generate_with_payload(name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return post_json(name, ENDPOINTS["generate_itinerary"], payload, TIMEOUTS["generate_itinerary"])


def test_generate_with_sample_payload() -> bool:
    payload = {
        "latitude": 40.707074094216594,
        "longitude": -74.0016461429476,
        "selected_vibe": "dinner_date",
        "social_context": "couple",
        "cuisine_preferences": [
            "indian_north",
            "indian_south",
            "indian_north_aesthetic",
            "indian_south_aesthetic",
        ],
        "radius_meters": 3000,
        "local_time_start": "19:00",
    }
    data = generate_with_payload("Generate itinerary (sample payload)", payload)
    if not data:
        return False

    itinerary = data.get("itinerary", [])
    if not itinerary:
        print_result(False, "Generate itinerary returned no stops")
        return False

    # Check radius constraint with 15% buffer.
    radius_km = payload["radius_meters"] / 1000
    center_lat = payload["latitude"]
    center_lon = payload["longitude"]
    out_of_range = []
    for item in itinerary:
        try:
            lat = float(item.get("latitude"))
            lon = float(item.get("longitude"))
        except (TypeError, ValueError):
            continue
        dist_km = haversine_km(center_lat, center_lon, lat, lon)
        if dist_km > radius_km * 1.15:
            out_of_range.append((item.get("name"), dist_km))

    if out_of_range:
        names = ", ".join([f"{name or 'unknown'} ({dist:.2f}km)" for name, dist in out_of_range[:3]])
        print_result(False, f"Found venues outside radius: {names}")
        return False

    print_result(True, f"Generated {len(itinerary)} stops within radius {radius_km}km")
    return True


def test_itinerary_details_from_generated() -> bool:
    payload = {
        "latitude": 40.707074094216594,
        "longitude": -74.0016461429476,
        "selected_vibe": "dinner_date",
        "social_context": "couple",
        "radius_meters": 3000,
        "local_time_start": "19:00",
    }
    generated = generate_with_payload("Generate itinerary for details", payload)
    if not generated:
        return False

    itinerary = generated.get("itinerary", [])
    place_ids = [item.get("place_id") for item in itinerary if item.get("place_id")]
    if not place_ids:
        print_result(False, "No place_ids returned from itinerary to fetch details")
        return False

    details_payload = {"place_ids": place_ids[:6]}
    details = post_json("Itinerary details", ENDPOINTS["itinerary_details"], details_payload, TIMEOUTS["itinerary_details"])
    if not details:
        return False

    venues = details.get("venues", [])
    if not venues:
        print_result(False, "Itinerary details returned empty venues array")
        return False

    required_fields = ["place_id", "name", "address", "insights"]
    missing = [v["place_id"] for v in venues if not all(f in v for f in required_fields)]
    if missing:
        print_result(False, f"Venue details missing fields for: {missing[:3]}")
        return False

    print_result(True, f"Fetched {len(venues)} venue details for {len(details_payload['place_ids'])} place_ids")
    return True


# --- End-to-end flow ---
def summarize_itinerary(itinerary: List[Dict[str, Any]]) -> None:
    if not itinerary:
        print_result(False, "No itinerary items to summarize")
        return
    print_kv(
        "Itinerary snapshot",
        [
            ("stops", str(len(itinerary))),
            ("first_stop", itinerary[0].get("name", "unknown")),
            ("first_slot", itinerary[0].get("slot", "unknown")),
        ],
    )
    print("  Top 3 stops:")
    for idx, item in enumerate(itinerary[:3], 1):
        name = item.get("name", "unknown")
        slot = item.get("slot", "unknown")
        rating = item.get("rating", "n/a")
        print(f"   {idx}. {name} | {slot} | rating={rating}")


def run_chained_flow_for_query(query: str, order_index: int) -> bool:
    print_section(f"Flow {order_index}: {query}")

    # Step 1: Parse
    parsed = post_json("Parse query", ENDPOINTS["parse_query"], {"query": query}, TIMEOUTS["parse_query"])
    if not parsed:
        return False

    location_hint = parsed.get("location_hint") or "soho"
    selected_vibe = parsed.get("selected_vibe") or "dinner_date"
    social_context = parsed.get("social_context") or "couple"
    cuisine_preferences = parsed.get("cuisine_preferences") or []
    time_pref = parsed.get("time_preference")

    print_kv(
        "Parsed intent",
        [
            ("location_hint", str(location_hint)),
            ("selected_vibe", str(selected_vibe)),
            ("social_context", str(social_context)),
            ("time_preference", str(time_pref)),
            ("cuisine_count", str(len(cuisine_preferences))),
        ],
    )

    # Step 2: Geocode
    geocoded = post_json("Geocode location", ENDPOINTS["geocode_location"], {"location_hint": location_hint}, TIMEOUTS["geocode_location"])
    if not geocoded:
        return False

    lat = geocoded.get("latitude")
    lon = geocoded.get("longitude")
    if lat is None or lon is None:
        print_result(False, "Geocode did not return latitude/longitude")
        return False

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        print_result(False, f"Geocode returned invalid coordinates: {lat}, {lon}")
        return False

    if not in_nyc_bounds(lat_f, lon_f):
        print_result(False, f"Geocoded point outside NYC bounds: ({lat_f:.4f}, {lon_f:.4f})")
        return False

    # Step 3: Generate itinerary (connected to previous responses)
    generate_payload = {
        "latitude": lat_f,
        "longitude": lon_f,
        "selected_vibe": selected_vibe,
        "social_context": social_context,
        "radius_meters": 3000,
        "local_time_start": "19:00",
    }
    if cuisine_preferences:
        generate_payload["cuisine_preferences"] = cuisine_preferences

    generated = generate_with_payload("Generate itinerary", generate_payload)
    if not generated:
        return False

    itinerary = generated.get("itinerary", [])
    if not itinerary:
        print_result(False, "Generate itinerary returned no stops")
        return False

    summarize_itinerary(itinerary)

    # Step 4: Itinerary details (connected to previous response)
    place_ids = [item.get("place_id") for item in itinerary if item.get("place_id")]
    if not place_ids:
        print_result(False, "No place_ids returned from itinerary")
        return False

    details = post_json("Itinerary details", ENDPOINTS["itinerary_details"], {"place_ids": place_ids[:6]}, TIMEOUTS["itinerary_details"])
    if not details:
        return False

    venues = details.get("venues", [])
    if not venues:
        print_result(False, "Itinerary details returned empty venues array")
        return False

    # Basic sanity check: required fields present
    required_fields = ["place_id", "name", "address", "insights"]
    missing = [v.get("place_id") for v in venues if not all(f in v for f in required_fields)]
    if missing:
        print_result(False, f"Venue details missing fields for: {missing[:3]}")
        return False

    print_kv("Venue details", [("count", str(len(venues))), ("sample", venues[0].get("name", "unknown"))])
    print_result(True, f"Flow {order_index} succeeded")
    return True


def main() -> None:
    print_section(f"API end-to-end tests against {BASE_URL}")

    # Sequential pre-flight tests (fast validation)
    preflight = [
        ("Geocode returns valid coords", test_geocode_returns_valid_coords),
        ("Geocode randomization varies", test_geocode_randomization_varies),
        ("Geocode requires hint", test_geocode_requires_hint),
        ("Parse query maps fields", test_parse_query_maps_fields),
        ("Generate itinerary with sample payload", test_generate_with_sample_payload),
        ("Itinerary details from generated itinerary", test_itinerary_details_from_generated),
    ]

    passed = 0
    for name, fn in preflight:
        print(f"\n{CYAN}Running: {name}{RESET}")
        try:
            if fn():
                passed += 1
        except Exception as exc:
            print_result(False, f"{name} raised exception: {exc}")

    print_kv("Preflight summary", [("passed", f"{passed}/{len(preflight)}")])

    # Chained flows in the exact order provided, with edge cases to stress parsing.
    queries = [
        "romantic indian places in soho",
        "cheap sushi near me",  # missing location
        "late night tacos 2am in queens",  # time + location
        "family friendly brunch with stroller in brooklyn",
        "quiet cafe to work in dumbo with outlets",
        "italian or thai, surprise me, near union square",
        "vegan pizza not too pricey in williamsburg",
        "cozy date night spot with cocktails, no loud music",
        "I want something spicy, South Indian vibes, downtown",
        "best speakeasy-ish bar, but not too crowded",
        "random",  # minimal input
        "asdf qwerty 123",  # nonsense input
    ]

    flow_passed = 0
    for idx, query in enumerate(queries, 1):
        try:
            if run_chained_flow_for_query(query, idx):
                flow_passed += 1
        except Exception as exc:
            print_result(False, f"Flow {idx} raised exception: {exc}")

    print_section("Final summary")
    print_kv(
        "Results",
        [
            ("preflight_passed", f"{passed}/{len(preflight)}"),
            ("flows_passed", f"{flow_passed}/{len(queries)}"),
            ("total_passed", f"{passed + flow_passed}/{len(preflight) + len(queries)}"),
        ],
    )


if __name__ == "__main__":
    main()
