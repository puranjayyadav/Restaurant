"""
Integration tests that hit live endpoints.

Run:
  BASE_URL=http://localhost:8000 pytest -m integration
"""

import os
from typing import Any, Dict, List

import pytest
import requests

BASE_URL = os.getenv("BASE_URL")


def require_base_url() -> str:
    if not BASE_URL:
        pytest.skip("BASE_URL not set; skipping integration tests")
    return BASE_URL.rstrip("/")


def post_json(url: str, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


@pytest.mark.integration
def test_parse_query_integration() -> None:
    base = require_base_url()
    data = post_json(
        f"{base}/api/api/parse-query/",
        {"query": "romantic indian places in soho"},
        timeout=30,
    )
    assert "selected_vibe" in data
    assert "cuisine_preferences" in data
    assert "location_hint" in data


@pytest.mark.integration
def test_geocode_location_integration() -> None:
    base = require_base_url()
    data = post_json(
        f"{base}/api/api/geocode-location/",
        {"location_hint": "soho"},
        timeout=20,
    )
    assert "latitude" in data and "longitude" in data


@pytest.mark.integration
def test_generate_itinerary_integration() -> None:
    base = require_base_url()
    data = post_json(
        f"{base}/api/api/generate-itinerary/",
        {
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
        },
        timeout=180,
    )
    assert "itinerary" in data
    assert isinstance(data["itinerary"], list)
    assert len(data["itinerary"]) > 0


@pytest.mark.integration
def test_itinerary_details_integration() -> None:
    base = require_base_url()
    generated = post_json(
        f"{base}/api/api/generate-itinerary/",
        {
            "latitude": 40.707074094216594,
            "longitude": -74.0016461429476,
            "selected_vibe": "dinner_date",
            "social_context": "couple",
            "radius_meters": 3000,
            "local_time_start": "19:00",
        },
        timeout=180,
    )
    itinerary: List[Dict[str, Any]] = generated.get("itinerary", [])
    place_ids = [item.get("place_id") for item in itinerary if item.get("place_id")]
    assert place_ids, "No place_ids returned from generate-itinerary"

    details = post_json(
        f"{base}/api/api/itinerary-details/",
        {"place_ids": place_ids[:6]},
        timeout=60,
    )
    assert "venues" in details
    assert len(details["venues"]) > 0


@pytest.mark.integration
def test_end_to_end_flow_integration() -> None:
    base = require_base_url()

    parsed = post_json(
        f"{base}/api/api/parse-query/",
        {"query": "romantic indian places in soho"},
        timeout=30,
    )
    location_hint = parsed.get("location_hint") or "soho"
    selected_vibe = parsed.get("selected_vibe") or "dinner_date"
    social_context = parsed.get("social_context") or "couple"
    cuisine_preferences = parsed.get("cuisine_preferences") or []

    geocoded = post_json(
        f"{base}/api/api/geocode-location/",
        {"location_hint": location_hint},
        timeout=20,
    )
    lat = geocoded.get("latitude")
    lon = geocoded.get("longitude")
    assert lat is not None and lon is not None

    payload = {
        "latitude": lat,
        "longitude": lon,
        "selected_vibe": selected_vibe,
        "social_context": social_context,
        "radius_meters": 3000,
        "local_time_start": "19:00",
    }
    if cuisine_preferences:
        payload["cuisine_preferences"] = cuisine_preferences

    generated = post_json(
        f"{base}/api/api/generate-itinerary/",
        payload,
        timeout=180,
    )
    itinerary: List[Dict[str, Any]] = generated.get("itinerary", [])
    place_ids = [item.get("place_id") for item in itinerary if item.get("place_id")]
    assert place_ids, "No place_ids returned from generate-itinerary"

    details = post_json(
        f"{base}/api/api/itinerary-details/",
        {"place_ids": place_ids[:6]},
        timeout=60,
    )
    assert "venues" in details
    assert len(details["venues"]) > 0
