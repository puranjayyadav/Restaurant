# Pre-Created Itineraries API Endpoints

## Overview
These endpoints expose pre-created itineraries for the discovery page in your Flutter app.

## Base URL
- **Local Development**: `http://localhost:8000/api/`
- **Production**: `https://restaurant-production-3aa0.up.railway.app/api/`

## Endpoints

### 1. Get Featured Itineraries
**Endpoint**: `GET /api/discovery/featured-itineraries/`

Get featured pre-created itineraries for the home/discovery page.

**Query Parameters**:
- `limit` (optional, default: 8): Number of itineraries to return
- `include_all` (optional, default: false): If true, also returns non-featured itineraries

**Example Request**:
```
GET /api/discovery/featured-itineraries/?limit=8
```

**Example Response**:
```json
{
  "featured_itineraries": [
    {
      "id": 1,
      "title": "Italian Food Tour",
      "description": "Discover the best Italian restaurants",
      "subtitle": "East Village • Italian",
      "cuisine": "Italian",
      "price_range": "$30 and under",
      "neighborhood": "East Village",
      "restaurant_count": 10,
      "enriched_count": 10,
      "enrichment_percentage": 100.0,
      "sample_image_url": "https://...",
      "latitude": 40.7262,
      "longitude": -73.9818,
      "radius_km": 1.0,
      "tags": ["Neighborhood gem"],
      "is_featured": true,
      "itinerary_data": {
        "itinerary": [
          {
            "place_name": "Restaurant Name",
            "address": "123 Main St",
            "latitude": 40.7262,
            "longitude": -73.9818,
            "rating": 4.5,
            "price_range": "$",
            "time_slot": "evening",
            "is_enriched": true,
            "postgres_data": {
              "menu_items": [...],
              "reviews": [...],
              "tags": [...],
              "features": [...],
              "photos": [...],
              "about": "...",
              "hours": {...},
              "categories": [...],
              "phone": "...",
              "website": "..."
            },
            "enrichment_metadata": {
              "has_menu": true,
              "has_reviews": true,
              "has_tags": true,
              "data_quality_score": 85
            }
          }
        ],
        "enrichment_stats": {
          "total_restaurants": 10,
          "enriched_count": 10,
          "enrichment_percentage": 100.0
        },
        "route_stats": {
          "total_distance_km": 2.5,
          "avg_distance_between": 0.28
        }
      },
      "created_at": "2025-12-04T12:00:00Z"
    }
  ],
  "all_itineraries": [],
  "total_featured": 1,
  "total_all": 1
}
```

### 2. Get All Pre-Created Itineraries (with filters)
**Endpoint**: `GET /api/discovery/pre-created-itineraries/`

Get all pre-created itineraries with optional filtering.

**Query Parameters**:
- `cuisine` (optional): Filter by cuisine type (e.g., "Italian", "French")
- `price_range` (optional): Filter by price range (e.g., "$30 and under", "$31-$50")
- `min_rating` (optional): Minimum rating (0-5)
- `tags` (optional): Comma-separated tags (e.g., "Romantic,Outdoor Seating")
- `latitude` (optional): User latitude for location filtering
- `longitude` (optional): User longitude for location filtering
- `radius_km` (optional, default: 10.0): Search radius in kilometers
- `limit` (optional, default: 20): Maximum number of results

**Example Request**:
```
GET /api/discovery/pre-created-itineraries/?cuisine=Italian&price_range=$30 and under&limit=10
```

**Example Response**:
```json
{
  "itineraries": [
    {
      "id": 1,
      "title": "Italian Food Tour",
      "description": "Discover the best Italian restaurants",
      "subtitle": "East Village • Italian",
      "cuisine": "Italian",
      "price_range": "$30 and under",
      "min_rating": 4.0,
      "tags": ["Neighborhood gem"],
      "latitude": 40.7262,
      "longitude": -73.9818,
      "radius_km": 1.0,
      "neighborhood": "East Village",
      "restaurant_count": 10,
      "enriched_count": 10,
      "enrichment_percentage": 100.0,
      "is_featured": true,
      "sample_image_url": "https://...",
      "itinerary_data": {...},
      "created_at": "2025-12-04T12:00:00Z",
      "last_updated": "2025-12-04T12:00:00Z"
    }
  ],
  "total": 1
}
```

### 3. Get Single Itinerary Detail
**Endpoint**: `GET /api/discovery/pre-created-itineraries/<itinerary_id>/`

Get detailed information about a specific pre-created itinerary.

**Example Request**:
```
GET /api/discovery/pre-created-itineraries/1/
```

**Example Response**:
```json
{
  "id": 1,
  "title": "Italian Food Tour",
  "description": "Discover the best Italian restaurants",
  "subtitle": "East Village • Italian",
  "cuisine": "Italian",
  "price_range": "$30 and under",
  "min_rating": 4.0,
  "neighborhood": "East Village",
  "restaurant_count": 10,
  "enriched_count": 10,
  "enrichment_percentage": 100.0,
  "sample_image_url": "https://...",
  "latitude": 40.7262,
  "longitude": -73.9818,
  "radius_km": 1.0,
  "tags": ["Neighborhood gem"],
  "is_featured": true,
  "itinerary_data": {
    "itinerary": [...],
    "enrichment_stats": {...},
    "route_stats": {...}
  },
  "created_at": "2025-12-04T12:00:00Z",
  "last_updated": "2025-12-04T12:00:00Z"
}
```

## Usage in Flutter

### Example: Fetching Featured Itineraries
```dart
final ApiService apiService = ApiService();
final itineraries = await apiService.getFeaturedItineraries(limit: 8);
```

### Example: Fetching with Filters
```dart
final itineraries = await apiService.getPreCreatedItineraries(
  cuisine: 'Italian',
  priceRange: '\$30 and under',
  minRating: 4.0,
  limit: 10,
);
```

## Error Responses

All endpoints return standard HTTP status codes:
- `200 OK`: Success
- `404 NOT FOUND`: Itinerary not found (for detail endpoint)
- `500 INTERNAL SERVER ERROR`: Server error

Error response format:
```json
{
  "error": "Error message here"
}
```

## Notes

- All endpoints are public (no authentication required)
- The `itinerary_data` field contains the full itinerary with all restaurant details
- Featured itineraries are automatically sorted by creation date (newest first)
- Location filtering uses a bounding box approximation for performance

