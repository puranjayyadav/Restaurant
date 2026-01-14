"""
Pytest unit tests for core API endpoints.
These tests use the Django test client and mock external calls.
"""

import json
from typing import Any, Dict

import pytest
import requests
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


class DummyResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("error", response=self)

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_parse_query_requires_query(api_client: APIClient) -> None:
    resp = api_client.post("/api/api/parse-query/", {}, format="json")
    assert resp.status_code == 400
    assert "query" in resp.data.get("error", "").lower()


def test_parse_query_success(api_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    llm_content = json.dumps(
        {
            "selected_vibe": "dinner_date",
            "cuisine_preferences": ["indian_north"],
            "social_context": "couple",
            "location_hint": "SoHo",
            "time_preference": "evening",
            "parsed_intent": "Romantic Indian dinner in SoHo",
        }
    )

    def fake_post(*_args: Any, **_kwargs: Any) -> DummyResponse:
        return DummyResponse({"choices": [{"message": {"content": llm_content}}]})

    monkeypatch.setattr(requests, "post", fake_post)

    resp = api_client.post(
        "/api/api/parse-query/",
        {"query": "romantic indian places in soho"},
        format="json",
    )

    assert resp.status_code == 200
    assert resp.data["selected_vibe"] == "dinner_date"
    assert resp.data["social_context"] == "couple"
    assert "cuisine_preferences" in resp.data
    assert any("indian" in slug for slug in resp.data["cuisine_preferences"])


def test_geocode_location_requires_hint(api_client: APIClient) -> None:
    resp = api_client.post("/api/api/geocode-location/", {}, format="json")
    assert resp.status_code == 400
    assert "location_hint" in resp.data.get("error", "").lower()


def test_geocode_location_success(api_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "my_new_project.res_backend.geocoding_service.geocode_with_randomization",
        lambda _hint: (40.7128, -74.0060),
    )
    monkeypatch.setattr(
        "my_new_project.res_backend.geocoding_service.is_within_nyc_bounds",
        lambda _lat, _lon: True,
    )

    resp = api_client.post("/api/api/geocode-location/", {"location_hint": "soho"}, format="json")
    assert resp.status_code == 200
    assert resp.data["base_location"] == "soho"
    assert "latitude" in resp.data and "longitude" in resp.data


def test_generate_itinerary_invalid_social_context(api_client: APIClient) -> None:
    resp = api_client.post(
        "/api/api/generate-itinerary/",
        {
            "latitude": 40.707074094216594,
            "longitude": -74.0016461429476,
            "selected_vibe": "dinner_date",
            "social_context": "aliens",
            "radius_meters": 3000,
            "local_time_start": "19:00",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "social_context" in resp.data.get("error", "").lower()


def test_generate_itinerary_success(api_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "my_new_project.res_backend.day_planner_service.get_supabase_client",
        lambda: None,
    )

    def fake_generate(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return {
            "itinerary": [
                {
                    "slot": "dinner",
                    "time": "7:00 PM",
                    "place_id": "place_1",
                    "name": "Test Restaurant",
                    "latitude": 40.71,
                    "longitude": -74.0,
                    "rating": 4.5,
                },
                {
                    "slot": "nightlife",
                    "time": "9:00 PM",
                    "place_id": "place_2",
                    "name": "Test Bar",
                    "latitude": 40.715,
                    "longitude": -74.01,
                    "rating": 4.6,
                },
            ],
            "hidden_gems_injected": 1,
            "total_walk_time_mins": 15,
            "narrative": "A romantic night out.",
        }

    monkeypatch.setattr(
        "my_new_project.res_backend.day_planner_service.DayPlannerService.generate_itinerary",
        fake_generate,
    )

    resp = api_client.post(
        "/api/api/generate-itinerary/",
        {
            "latitude": 40.707074094216594,
            "longitude": -74.0016461429476,
            "selected_vibe": "dinner_date",
            "social_context": "couple",
            "radius_meters": 3000,
            "local_time_start": "19:00",
        },
        format="json",
    )

    assert resp.status_code == 200
    assert "itinerary" in resp.data
    assert len(resp.data["itinerary"]) == 2


def test_itinerary_details_validations(api_client: APIClient) -> None:
    resp = api_client.post("/api/api/itinerary-details/", {}, format="json")
    assert resp.status_code == 400

    resp = api_client.post("/api/api/itinerary-details/", {"place_ids": "not-a-list"}, format="json")
    assert resp.status_code == 400

    resp = api_client.post("/api/api/itinerary-details/", {"place_ids": ["x"] * 21}, format="json")
    assert resp.status_code == 400


def test_itinerary_details_success(api_client: APIClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "my_new_project.res_backend.day_planner_service.get_supabase_client",
        lambda: None,
    )

    def fake_details(_self: Any, place_ids: Any) -> Any:
        return [
            {
                "place_id": place_ids[0],
                "name": "Test Venue",
                "address": "123 Test St",
                "insights": {"display_hook": "Great vibes"},
            }
        ]

    monkeypatch.setattr(
        "my_new_project.res_backend.day_planner_service.DayPlannerService.get_venue_details",
        fake_details,
    )

    resp = api_client.post(
        "/api/api/itinerary-details/",
        {"place_ids": ["ChIJTEST123"]},
        format="json",
    )
    assert resp.status_code == 200
    assert "venues" in resp.data
    assert resp.data["venues"][0]["place_id"] == "ChIJTEST123"
