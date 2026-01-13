# Architecture: Vibe-Based Itinerary Logic

## System Overview

```
┌─────────────────┐
│  Flutter App    │
│  (Frontend)     │
└────────┬────────┘
         │
         │ HTTP Request
         │ {flow_type, vibe_slug, location}
         │
         ▼
┌─────────────────────────────────────────┐
│  FastAPI Backend                        │
│  ┌───────────────────────────────────┐  │
│  │  /api/generate-itinerary/         │  │
│  │  - Validate request               │  │
│  │  - Route to appropriate flow      │  │
│  └──────────┬────────────────────────┘  │
│             │                            │
│    ┌────────┴────────┐                  │
│    │                 │                  │
│    ▼                 ▼                  │
│  ┌──────────┐   ┌──────────┐           │
│  │ Flow A   │   │ Flow B   │           │
│  │ Quick    │   │ Context  │           │
│  │ Search   │   │ Search   │           │
│  └────┬─────┘   └────┬─────┘           │
│       │              │                  │
│       │              │                  │
│       ▼              ▼                  │
│  ┌─────────────────────────┐           │
│  │  Vibe Mapper Service    │           │
│  │  - Map filters to slugs │           │
│  │  - Fuzzy match queries  │           │
│  └──────────┬──────────────┘           │
│             │                            │
│             ▼                            │
│  ┌─────────────────────────┐           │
│  │  Location Service       │           │
│  │  - Random neighborhood  │           │
│  │  - User location        │           │
│  └──────────┬──────────────┘           │
│             │                            │
│             ▼                            │
│  ┌─────────────────────────┐           │
│  │  Itinerary Solver       │           │
│  │  - Query venue_vibes    │           │
│  │  - Filter by location   │           │
│  │  - Rank & select 4      │           │
│  └──────────┬──────────────┘           │
│             │                            │
└─────────────┼────────────────────────────┘
              │
              ▼
      ┌───────────────┐
      │   Supabase    │
      │  venue_vibes  │
      │     table     │
      └───────────────┘
```

## Component Breakdown

### Frontend Components

#### 1. PlanditAskAISection
**Responsibility**: Handle quick filter button clicks
```dart
class PlanditAskAISection extends StatefulWidget {
  // Quick filter buttons
  final List<QuickFilter> quickFilters = [
    QuickFilter('Coffee Run', 'coffee_run'),
    QuickFilter('Work Friendly', 'work_friendly'),
    QuickFilter('Breakfast Classic', 'breakfast_classic'),
    QuickFilter('Brunch Spot', 'brunch_buzzy'),
    QuickFilter('Date Night', 'dinner_date'),
  ];
  
  void _handleQuickFilter(QuickFilter filter) {
    apiService.generateItinerary(
      flowType: 'quick_search',
      vibeSlug: filter.slug,
      quickFilter: filter.name,
    );
  }
}
```

#### 2. Search Bar Handler
**Responsibility**: Process manual queries
```dart
void _handleSearchSubmit(String query) {
  final location = await _getCurrentLocation();
  
  apiService.generateItinerary(
    flowType: 'contextual',
    query: query,
    location: location,
  );
}
```

### Backend Components

#### 1. vibe_mapper.py
**Responsibility**: Map UI inputs to vibe_slug values

```python
QUICK_FILTER_MAP = {
    "Coffee Run": "coffee_run",
    "Work Friendly": "work_friendly",
    "Breakfast Classic": "breakfast_classic",
    "Brunch Spot": "brunch_buzzy",
    "Date Night": "dinner_date",
}

FUZZY_MATCH_RULES = {
    "korean bbq": "korean_bbq",
    "italian": ["italian_red_sauce", "italian_regional"],
    "coffee": ["coffee_run", "coffee"],
    "brunch": "brunch_buzzy",
    # ... 91 total mappings
}

def parse_query_to_vibe(query: str) -> Optional[str]:
    """
    Fuzzy match user query to vibe_slug.
    Returns best matching vibe_slug or None.
    """
    query_lower = query.lower()
    
    # Exact match
    if query_lower in FUZZY_MATCH_RULES:
        return FUZZY_MATCH_RULES[query_lower]
    
    # Partial match with scoring
    best_match = None
    best_score = 0
    
    for keyword, vibe in FUZZY_MATCH_RULES.items():
        if keyword in query_lower:
            score = len(keyword) / len(query_lower)
            if score > best_score:
                best_score = score
                best_match = vibe
    
    return best_match
```

#### 2. nyc_neighborhoods.py
**Responsibility**: Manage NYC neighborhood data

```python
NYC_NEIGHBORHOODS = [
    {"name": "West Village", "lat": 40.7358, "lng": -74.0036, "radius_km": 1.5},
    {"name": "Williamsburg", "lat": 40.7081, "lng": -73.9571, "radius_km": 2.0},
    # ... 15 total neighborhoods
]

def get_random_neighborhood() -> dict:
    """
    Randomly select a popular NYC neighborhood.
    Returns dict with name, lat, lng, radius_km.
    """
    return random.choice(NYC_NEIGHBORHOODS)

def get_neighborhood_bounds(neighborhood: dict) -> tuple:
    """
    Calculate bounding box for neighborhood.
    Returns (min_lat, max_lat, min_lng, max_lng).
    """
    lat, lng, radius = neighborhood['lat'], neighborhood['lng'], neighborhood['radius_km']
    # Convert radius to lat/lng degrees
    lat_delta = radius / 111.0  # 1 degree ≈ 111km
    lng_delta = radius / (111.0 * math.cos(math.radians(lat)))
    
    return (
        lat - lat_delta,
        lat + lat_delta,
        lng - lng_delta,
        lng + lng_delta
    )
```

#### 3. itinerary_solver.py (Updated)
**Responsibility**: Core itinerary generation logic

```python
class ItinerarySolver:
    def generate_vibe_based_itinerary(
        self,
        flow_type: str,
        vibe_slug: str,
        location: Optional[dict] = None,
        quick_filter: Optional[str] = None
    ) -> dict:
        """
        Generate itinerary based on flow type.
        """
        if flow_type == "quick_search":
            return self._flow_a_quick_search(vibe_slug)
        elif flow_type == "contextual":
            return self._flow_b_contextual(vibe_slug, location)
        else:
            raise ValueError(f"Invalid flow_type: {flow_type}")
    
    def _flow_a_quick_search(self, vibe_slug: str) -> dict:
        """
        Flow A: Random neighborhood, ignore user location.
        """
        # 1. Select random neighborhood
        neighborhood = get_random_neighborhood()
        
        # 2. Query venues with this vibe in this neighborhood
        bounds = get_neighborhood_bounds(neighborhood)
        venues = self.supabase.query_venues_by_vibe(
            vibe_slug=vibe_slug,
            bounds=bounds,
            limit=4
        )
        
        # 3. Build itinerary
        return {
            "itinerary": venues,
            "metadata": {
                "flow_type": "quick_search",
                "neighborhood": neighborhood['name'],
                "vibe_slug": vibe_slug,
                "vibe_match_rate": 1.0
            }
        }
    
    def _flow_b_contextual(self, vibe_slug: str, location: dict) -> dict:
        """
        Flow B: User location, contextual search.
        """
        # 1. Use provided location or default
        lat = location.get('lat', 40.7589)  # Default to Manhattan
        lng = location.get('lng', -73.9851)
        
        # 2. Query venues with this vibe near user
        venues = self.supabase.query_venues_by_vibe(
            vibe_slug=vibe_slug,
            center=(lat, lng),
            radius_km=3.0,
            limit=4
        )
        
        # 3. If < 4 venues, expand radius
        if len(venues) < 4:
            venues = self.supabase.query_venues_by_vibe(
                vibe_slug=vibe_slug,
                center=(lat, lng),
                radius_km=5.0,
                limit=4
            )
        
        # 4. Build itinerary
        return {
            "itinerary": venues,
            "metadata": {
                "flow_type": "contextual",
                "vibe_slug": vibe_slug,
                "user_location": location,
                "vibe_match_rate": len(venues) / 4.0
            }
        }
```

#### 4. supabase_client.py (New Method)
**Responsibility**: Database queries

```python
def query_venues_by_vibe(
    self,
    vibe_slug: str,
    bounds: Optional[tuple] = None,
    center: Optional[tuple] = None,
    radius_km: Optional[float] = None,
    limit: int = 4
) -> List[dict]:
    """
    Query venues from venue_vibes table.
    
    Args:
        vibe_slug: The vibe to filter by
        bounds: (min_lat, max_lat, min_lng, max_lng) for bounding box
        center: (lat, lng) for radius search
        radius_km: Radius in km for radius search
        limit: Max number of results
    
    Returns:
        List of venue dicts with place data
    """
    query = self.client.table('venue_vibes') \
        .select('*, places(*)') \
        .eq('vibe_slug', vibe_slug)
    
    if bounds:
        min_lat, max_lat, min_lng, max_lng = bounds
        query = query.gte('places.lat', min_lat) \
                     .lte('places.lat', max_lat) \
                     .gte('places.lng', min_lng) \
                     .lte('places.lng', max_lng)
    
    if center and radius_km:
        # Use PostGIS for radius search
        lat, lng = center
        query = query.rpc('nearby_places', {
            'lat': lat,
            'lng': lng,
            'radius_km': radius_km
        })
    
    result = query.limit(limit).execute()
    return result.data
```

## Data Flow

### Flow A: Quick Search
1. User clicks "Coffee Run" button
2. Frontend sends: `{flow_type: "quick_search", vibe_slug: "coffee_run"}`
3. Backend randomly selects "Williamsburg"
4. Backend queries `venue_vibes` WHERE `vibe_slug = 'coffee_run'` AND location in Williamsburg bounds
5. Backend returns 4 coffee shops in Williamsburg
6. Frontend displays in `PlanditStoryboardView`

### Flow B: Contextual Search
1. User types "Korean BBQ in Koreatown"
2. Frontend gets user location: `{lat: 40.7489, lng: -73.9680}`
3. Frontend sends: `{flow_type: "contextual", query: "Korean BBQ in Koreatown", location: {...}}`
4. Backend fuzzy matches "Korean BBQ" → `korean_bbq`
5. Backend queries `venue_vibes` WHERE `vibe_slug = 'korean_bbq'` AND within 3km of user location
6. Backend returns 4 Korean BBQ spots near user
7. Frontend displays in `PlanditStoryboardView`

## Database Schema

### venue_vibes Table
```sql
CREATE TABLE venue_vibes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  place_id TEXT NOT NULL REFERENCES places(place_id),
  vibe_slug TEXT NOT NULL,
  confidence_score FLOAT DEFAULT 1.0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_venue_vibes_slug ON venue_vibes(vibe_slug);
CREATE INDEX idx_venue_vibes_place ON venue_vibes(place_id);
CREATE INDEX idx_venue_vibes_composite ON venue_vibes(vibe_slug, place_id);
```

### places Table (Existing)
```sql
CREATE TABLE places (
  place_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  lat FLOAT NOT NULL,
  lng FLOAT NOT NULL,
  category TEXT,
  rating FLOAT,
  price_range TEXT,
  -- ... other fields
);

CREATE INDEX idx_places_location ON places USING GIST (
  ll_to_earth(lat, lng)
);
```

## Performance Optimizations

1. **Indexing**: Composite index on `(vibe_slug, place_id)` for fast lookups
2. **Caching**: Cache popular vibe queries (coffee_run, dinner_date) for 1 hour
3. **Connection Pooling**: Maintain Supabase connection pool for concurrent requests
4. **Query Optimization**: Use PostGIS for efficient radius searches
5. **Lazy Loading**: Load venue details only when user clicks on result

## Error Handling Strategy

1. **No Venues Found**: Return empty itinerary with helpful suggestion
2. **Invalid Vibe Slug**: Log warning, fall back to general search
3. **Database Timeout**: Return cached results if available, else error
4. **Location Unavailable**: Default to Manhattan center coordinates
5. **API Rate Limit**: Return 429 with retry-after header
