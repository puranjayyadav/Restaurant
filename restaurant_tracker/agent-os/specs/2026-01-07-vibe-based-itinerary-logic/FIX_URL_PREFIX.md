# Fix: URL Path Prefix

## Issue
The frontend received a 404 error when calling `generateVibeItinerary`.
Log analysis showed: `DEBUG: Status Code: 404` and receiving HTML (Django 404 page).

## Root Cause
The `ApiService` constructed the URL as `$baseUrl/generate-vibe-itinerary/`.
However, the Django backend routes are configured under the `/api/` prefix in the main `urls.py`:
```python
path('api/', include('res_backend.urls')),
```
So the correct URL is `$baseUrl/api/generate-vibe-itinerary/`.

## Resolution
Updated `lib/api_service.dart` to include `/api/` in the URI parsing for `generateVibeItinerary`.

## Verification
1. Rerun `flutter run` (hot reload might be sufficient if `ApiService` is reloaded, but hot restart recommended).
2. Trigger the action again.
3. Expect functionality to work as backend tests passed with the `/api/` prefix.
