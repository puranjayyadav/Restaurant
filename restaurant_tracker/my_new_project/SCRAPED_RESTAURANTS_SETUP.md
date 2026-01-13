# Scraped Restaurants Database Setup

## Overview

This setup adds PostgreSQL database models and API endpoints for storing and querying restaurant data scraped from multiple sources (Yelp, Google Maps, TripAdvisor, etc.).

## What Was Added

### 1. Database Models (`res_backend/models.py`)

#### `ScrapedRestaurant`
- Stores restaurant data from multiple sources
- Includes location data (lat/long for geospatial queries)
- Flexible JSON fields for hours, categories, features, photos, etc.
- Data quality scoring
- Deduplication support

#### `RestaurantDeduplication`
- Tracks potential duplicate restaurants
- Similarity scoring
- Manual verification support

### 2. Admin Interface (`res_backend/admin.py`)
- Full admin interface for managing scraped restaurants
- Filtering by source, city, state, verification status
- Search functionality
- Data quality score display

### 3. Management Command (`res_backend/management/commands/import_scraped_restaurants.py`)
- Bulk import restaurants from JSON files
- Supports multiple sources
- Dry-run mode for testing
- Automatic data quality scoring

### 4. API Endpoints (`res_backend/views.py` & `urls.py`)

#### GET `/api/scraped-restaurants/`
Query parameters:
- `city` - Filter by city
- `state` - Filter by state
- `source` - Filter by source (yelp, google, etc.)
- `min_rating` - Minimum rating
- `search` - Search by name/address
- `latitude`, `longitude`, `radius_km` - Geospatial filtering
- `limit` - Number of results (default 50, max 200)

#### GET `/api/scraped-restaurants/<id>/`
Get detailed information about a specific restaurant

#### POST `/api/scraped-restaurants/create/`
Create a new restaurant entry

## Setup Instructions

### 1. Create and Run Migrations

```bash
cd my_new_project
python manage.py makemigrations res_backend
python manage.py migrate
```

### 2. Import Data from Scrapers

#### Example JSON Format:
```json
[
  {
    "name": "Joe's Pizza",
    "source_id": "yelp_12345",
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "phone": "+1-212-555-1234",
    "website": "https://joespizza.com",
    "rating": 4.5,
    "total_reviews": 1250,
    "price_range": "$$",
    "categories": ["Pizza", "Italian"],
    "hours": {
      "monday": "11:00 AM - 10:00 PM",
      "tuesday": "11:00 AM - 10:00 PM"
    },
    "photos": ["https://...", "https://..."]
  }
]
```

#### Import Command:
```bash
# Import from Yelp
python manage.py import_scraped_restaurants restaurants_yelp.json --source yelp

# Import from Google Maps
python manage.py import_scraped_restaurants restaurants_google.json --source google

# Dry run (test without saving)
python manage.py import_scraped_restaurants restaurants.json --source yelp --dry-run
```

### 3. Access Admin Interface

1. Create superuser (if not exists):
```bash
python manage.py createsuperuser
```

2. Access admin at: `http://localhost:8000/admin/`
3. Navigate to "Scraped Restaurants" section

## API Usage Examples

### Get restaurants in New York
```
GET /api/scraped-restaurants/?city=New York&state=NY&limit=20
```

### Get restaurants near a location (within 5km)
```
GET /api/scraped-restaurants/?latitude=40.7128&longitude=-74.0060&radius_km=5
```

### Search restaurants by name
```
GET /api/scraped-restaurants/?search=pizza&city=New York
```

### Get high-rated restaurants
```
GET /api/scraped-restaurants/?min_rating=4.5&limit=50
```

### Get restaurants from specific source
```
GET /api/scraped-restaurants/?source=yelp&city=New York
```

### Get restaurant details
```
GET /api/scraped-restaurants/123/
```

## Response Format

### List Response:
```json
{
  "count": 20,
  "results": [
    {
      "id": 1,
      "name": "Joe's Pizza",
      "source": "yelp",
      "source_display": "Yelp",
      "city": "New York",
      "state": "NY",
      "latitude": "40.712800",
      "longitude": "-74.006000",
      "rating": "4.50",
      "total_reviews": 1250,
      "price_range": "$$",
      "is_verified": false,
      "data_quality_score": 80,
      "distance_km": 2.5  // Only if lat/lon provided
    }
  ]
}
```

### Detail Response:
```json
{
  "id": 1,
  "source": "yelp",
  "source_display": "Yelp",
  "source_id": "yelp_12345",
  "name": "Joe's Pizza",
  "description": "Best pizza in NYC",
  "address": "123 Main St",
  "city": "New York",
  "state": "NY",
  "latitude": "40.712800",
  "longitude": "-74.006000",
  "rating": "4.50",
  "total_reviews": 1250,
  "price_range": "$$",
  "phone": "+1-212-555-1234",
  "website": "https://joespizza.com",
  "hours": {
    "monday": "11:00 AM - 10:00 PM"
  },
  "categories": ["Pizza", "Italian"],
  "features": ["outdoor_seating", "wifi"],
  "photos": ["https://..."],
  "data_quality_score": 80,
  "is_verified": false,
  "is_active": true
}
```

## Data Quality Scoring

The system automatically calculates a data quality score (0-100) based on:
- Basic info (name, address, coordinates): 30 points
- Contact info (phone, website): 20 points
- Ratings (rating, reviews): 20 points
- Rich data (hours, categories, photos): 30 points

## Deduplication

To handle duplicate restaurants from different sources:
1. Use `RestaurantDeduplication` model to track potential duplicates
2. Link duplicates using `duplicate_of` field
3. Only canonical restaurants (without `duplicate_of`) appear in queries

## Performance

The models include indexes for:
- Geospatial queries (latitude, longitude)
- Location filtering (city, state)
- Rating queries
- Source filtering
- Name search

## Next Steps

1. **Run migrations** to create database tables
2. **Import your scraped data** using the management command
3. **Test API endpoints** with your Flutter app
4. **Set up deduplication** if scraping from multiple sources
5. **Monitor data quality** scores in admin interface

## Integration with Flutter App

Update your `api_service.dart` to use the new endpoints:

```dart
Future<List<dynamic>> getScrapedRestaurants({
  double? lat,
  double? lon,
  double radiusKm = 10.0,
  String? city,
  String? state,
  String? source,
  double? minRating,
  String? search,
}) async {
  final queryParams = <String, String>{};
  if (lat != null && lon != null) {
    queryParams['latitude'] = lat.toString();
    queryParams['longitude'] = lon.toString();
    queryParams['radius_km'] = radiusKm.toString();
  }
  if (city != null) queryParams['city'] = city;
  if (state != null) queryParams['state'] = state;
  if (source != null) queryParams['source'] = source;
  if (minRating != null) queryParams['min_rating'] = minRating.toString();
  if (search != null) queryParams['search'] = search;
  
  final url = Uri.parse('$baseUrl/api/scraped-restaurants/')
      .replace(queryParameters: queryParams);
  
  final response = await http.get(url);
  if (response.statusCode == 200) {
    final data = json.decode(response.body);
    return data['results'] as List<dynamic>;
  }
  return [];
}
```

