# Vibe-Based Itinerary API Reference

## Endpoint
```
POST /api/generate-vibe-itinerary/
```

## Request Format

### Flow A: Quick Search (Random Neighborhood)
```json
{
  "flow_type": "quick_search",
  "quick_filter": "Coffee Run"
}
```

**Quick Filter Options**:
- `"Coffee Run"` → `coffee_run` (1605 venues)
- `"Work Friendly"` → `work_friendly` (1755 venues)
- `"Breakfast Classic"` → `breakfast_classic` (1314 venues)
- `"Brunch Spot"` → `brunch_buzzy` (1082 venues)
- `"Date Night"` → `dinner_date` (999 venues)

### Flow B: Contextual (Location-Aware)
```json
{
  "flow_type": "contextual",
  "query": "Korean BBQ in Koreatown",
  "location": {
    "lat": 40.7489,
    "lng": -73.9680
  }
}
```

**Optional Parameters**:
- `vibe_slug`: Explicit vibe (overrides query parsing)
- `max_venues`: Number of venues to return (default: 4)

## Response Format

```json
{
  "itinerary": [
    {
      "slot": 1,
      "name": "Devoción",
      "category": "Coffee Shop",
      "lat": 40.7081,
      "lng": -73.9571,
      "reason": "A great coffee run spot",
      "rating": 4.6,
      "price_range": "$$",
      "place_id": "ChIJ...",
      "vibe_slug": "coffee_run",
      "photos": ["https://..."]
    }
  ],
  "metadata": {
    "flow_type": "quick_search",
    "neighborhood": "Williamsburg",
    "vibe_slug": "coffee_run",
    "vibe_match_rate": 1.0,
    "total_venues": 4,
    "quick_filter": "Coffee Run"
  }
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing required field: flow_type"
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to generate vibe itinerary: <error message>"
}
```

## Example Usage

### cURL
```bash
# Flow A
curl -X POST http://localhost:8000/api/generate-vibe-itinerary/ \
  -H "Content-Type: application/json" \
  -d '{"flow_type": "quick_search", "quick_filter": "Coffee Run"}'

# Flow B
curl -X POST http://localhost:8000/api/generate-vibe-itinerary/ \
  -H "Content-Type: application/json" \
  -d '{
    "flow_type": "contextual",
    "query": "Korean BBQ",
    "location": {"lat": 40.7489, "lng": -73.9680}
  }'
```

### Python
```python
import requests

# Flow A
response = requests.post(
    'http://localhost:8000/api/generate-vibe-itinerary/',
    json={
        'flow_type': 'quick_search',
        'quick_filter': 'Coffee Run'
    }
)

# Flow B
response = requests.post(
    'http://localhost:8000/api/generate-vibe-itinerary/',
    json={
        'flow_type': 'contextual',
        'query': 'Korean BBQ in Koreatown',
        'location': {'lat': 40.7489, 'lng': -73.9680}
    }
)
```

### Flutter/Dart
```dart
final response = await http.post(
  Uri.parse('$baseUrl/generate-vibe-itinerary/'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'flow_type': 'quick_search',
    'quick_filter': 'Coffee Run',
  }),
);
```

## Available Vibe Slugs (Top 20)

| Vibe Slug | Venues | Description |
|-----------|--------|-------------|
| `casual_lunch` | 2108 | Casual lunch spots |
| `solo_date` | 2083 | Solo-friendly venues |
| `late_night_eats` | 1847 | Late night food |
| `work_friendly` | 1755 | Good for working |
| `coffee_run` | 1605 | Coffee shops |
| `art_house` | 1461 | Art galleries |
| `breakfast_classic` | 1314 | Classic breakfast |
| `dinner_group` | 1229 | Group dinners |
| `brunch_buzzy` | 1082 | Trendy brunch |
| `bakery_cafe` | 1017 | Bakeries & cafes |
| `natural_wine` | 1005 | Natural wine bars |
| `dinner_date` | 999 | Date night dining |
| `fine_dining` | 790 | Upscale dining |
| `dive_bar` | 760 | Dive bars |
| `urban_jungle` | 756 | Plant-filled spaces |
| `aesthetic` | 721 | Instagram-worthy |
| `speakeasy` | 692 | Hidden bars |
| `minimalist` | 595 | Minimalist design |
| `rooftop` | 531 | Rooftop venues |
| `korean_bbq` | 133 | Korean BBQ |

[See full list of 91 vibes in `vibe_mapper.py`]

## NYC Neighborhoods (Flow A)

When using Flow A, one of these neighborhoods is randomly selected:

1. West Village
2. Williamsburg
3. Astoria
4. SoHo
5. East Village
6. DUMBO
7. Park Slope
8. Greenpoint
9. Lower East Side
10. Nolita
11. Chelsea
12. Flatiron
13. Tribeca
14. Bushwick
15. Bed-Stuy

## Implementation Notes

- **Flow A** ignores user location and randomly selects a neighborhood
- **Flow B** uses user location or defaults to Manhattan (40.7589, -73.9851)
- **Vibe matching** uses fuzzy logic (e.g., "Korean BBQ" → `korean_bbq`)
- **Max venues** defaults to 4 but can be customized
- **Response time** target is < 2 seconds
- **Vibe match rate** should be 90%+ for quality results
