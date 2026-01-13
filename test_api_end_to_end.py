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
from typing import Any, Dict, List, Optional

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
RESET = "\033[0m"


def print_result(success: bool, message: str) -> None:
    color = GREEN if success else RED
    print(f"{color}{'[PASS]' if success else '[FAIL]'}{RESET} {message}")


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
    print(f"Payload: {payload}")
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
        print(f"Response ({duration:.2f}s): {data}")
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
def test_end_to_end_from_parse() -> bool:
    # Step 1: parse natural language query
    parsed = post_json("Parse query (E2E)", ENDPOINTS["parse_query"], {"query": "romantic indian places in soho"}, TIMEOUTS["parse_query"])
    if not parsed:
        return False

    location_hint = parsed.get("location_hint") or "soho"
    selected_vibe = parsed.get("selected_vibe") or "dinner_date"
    social_context = parsed.get("social_context") or "couple"
    cuisine_preferences = parsed.get("cuisine_preferences") or []

    # Step 2: geocode location
    geocoded = post_json("Geocode (E2E)", ENDPOINTS["geocode_location"], {"location_hint": location_hint}, TIMEOUTS["geocode_location"])
    if not geocoded:
        return False

    lat = geocoded.get("latitude")
    lon = geocoded.get("longitude")
    if lat is None or lon is None:
        print_result(False, "Geocode (E2E) did not return latitude/longitude")
        return False

    # Step 3: generate itinerary using parsed + geocoded data
    generate_payload = {
        "latitude": lat,
        "longitude": lon,
        "selected_vibe": selected_vibe,
        "social_context": social_context,
        "radius_meters": 3000,
        "local_time_start": "19:00",
    }
    if cuisine_preferences:
        generate_payload["cuisine_preferences"] = cuisine_preferences

    generated = generate_with_payload("Generate itinerary (E2E)", generate_payload)
    if not generated:
        return False

    itinerary = generated.get("itinerary", [])
    if not itinerary:
        print_result(False, "Generate itinerary (E2E) returned no stops")
        return False

    # Step 4: fetch details for returned place_ids
    place_ids = [item.get("place_id") for item in itinerary if item.get("place_id")]
    if not place_ids:
        print_result(False, "No place_ids from itinerary to fetch details (E2E)")
        return False

    details = post_json("Itinerary details (E2E)", ENDPOINTS["itinerary_details"], {"place_ids": place_ids[:6]}, TIMEOUTS["itinerary_details"])
    if not details:
        return False

    venues = details.get("venues", [])
    if not venues:
        print_result(False, "Itinerary details (E2E) returned empty venues array")
        return False

    print_result(True, f"E2E flow succeeded with {len(itinerary)} stops and {len(venues)} venue details")
    return True


def main() -> None:
    print(f"{YELLOW}Starting API end-to-end tests against {BASE_URL}{RESET}")
    tests = [
        ("Geocode returns valid coords", test_geocode_returns_valid_coords),
        ("Geocode randomization varies", test_geocode_randomization_varies),
        ("Geocode requires hint", test_geocode_requires_hint),
        ("Parse query maps fields", test_parse_query_maps_fields),
        ("Generate itinerary with sample payload", test_generate_with_sample_payload),
        ("Itinerary details from generated itinerary", test_itinerary_details_from_generated),
        ("Full end-to-end flow", test_end_to_end_from_parse),
    ]

    passed = 0
    for name, fn in tests:
        print(f"\n{CYAN}Running: {name}{RESET}")
        try:
            if fn():
                passed += 1
        except Exception as exc:
            print_result(False, f"{name} raised exception: {exc}")

    print(f"\n{YELLOW}Test summary: {passed}/{len(tests)} passed{RESET}")
    if passed == len(tests):
        print_result(True, "All endpoint tests passed")
    else:
        print_result(False, "Some endpoint tests failed (see above)")


if __name__ == "__main__":
    main()
