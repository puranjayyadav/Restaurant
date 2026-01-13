# Vibe-Based Itinerary Implementation Summary

## ✅ Completed Backend Work

### 1. Core Services Created

#### `vibe_mapper.py`
- **Location**: `my_new_project/res_backend/vibe_mapper.py`
- **Functions**:
  - `map_quick_filter(filter_name)` - Maps button names to vibe_slugs
  - `parse_query_to_vibe(query)` - Fuzzy matches queries to vibes
  - `get_all_vibe_slugs()` - Returns all 91 available vibes
  - `validate_vibe_slug(vibe_slug)` - Validates slug existence
- **Data**: Contains all 91 vibe_slugs with gem counts

#### `nyc_neighborhoods.py`
- **Location**: `my_new_project/res_backend/nyc_neighborhoods.py`
- **Functions**:
  - `get_random_neighborhood()` - Randomly selects NYC neighborhood
  - `get_neighborhood_bounds(neighborhood)` - Calculates bounding box
  - `calculate_distance_km(lat1, lng1, lat2, lng2)` - Haversine distance
  - `find_nearest_neighborhood(lat, lng)` - Finds closest neighborhood
- **Data**: 15 popular NYC neighborhoods with coordinates

#### `vibe_itinerary_solver.py`
- **Location**: `my_new_project/res_backend/vibe_itinerary_solver.py`
- **Main Function**: `generate_vibe_based_itinerary(flow_type, vibe_slug, ...)`
- **Flow A**: `_flow_a_quick_search()` - Random neighborhood logic
- **Flow B**: `_flow_b_contextual()` - Location-aware logic
- **Integration**: Uses existing `get_venues_from_supabase()` function

### 2. API Endpoint Code (Ready to Add)

**Endpoint**: `/api/generate-vibe-itinerary/`
**Method**: POST
**Location**: Add to `my_new_project/res_backend/views.py` (line ~3822)

```python
@api_view(['POST'])
@permission_classes([])
def generate_vibe_itinerary(request):
    """
    Generate vibe-based itinerary with two flows:
    - Flow A (Quick Search): Random NYC neighborhood, ignores user location
    - Flow B (Contextual): User location-aware search
    """
    from .vibe_itinerary_solver import generate_vibe_based_itinerary
    
    try:
        data = request.data
        flow_type = data.get('flow_type')
        vibe_slug = data.get('vibe_slug')
        quick_filter = data.get('quick_filter')
        query = data.get('query')
        location = data.get('location')
        max_venues = data.get('max_venues', 4)
        
        if not flow_type:
            return Response(
                {"error": "Missing required field: flow_type"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = generate_vibe_based_itinerary(
            flow_type=flow_type,
            vibe_slug=vibe_slug,
            quick_filter=quick_filter,
            query=query,
            location=location,
            max_venues=max_venues
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        print(f"[generate_vibe_itinerary] Error: {str(e)}")
        print(traceback.format_exc())
        return Response(
            {"error": f"Failed to generate vibe itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

### 3. URL Route (Ready to Add)

**File**: `my_new_project/res_backend/urls.py`

**Step 1**: Add to imports (line 14):
```python
from .views import (
    # ... existing imports ...
    parse_query_view, generate_vibe_itinerary  # Add this
)
```

**Step 2**: Add to urlpatterns (line 67):
```python
urlpatterns = [
    # ... existing patterns ...
    path('generate-vibe-itinerary/', generate_vibe_itinerary, name='generate-vibe-itinerary'),
]
```

## 🧪 Testing the Backend

### Test Script

Create `test_vibe_api.py` in `my_new_project/res_backend/`:

```python
"""
Test script for vibe-based itinerary API
Run with: python manage.py shell < test_vibe_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

# Test Flow A: Quick Search
print("=== Testing Flow A: Quick Search ===")
flow_a_request = {
    "flow_type": "quick_search",
    "quick_filter": "Coffee Run"
}

response_a = requests.post(
    f"{BASE_URL}/generate-vibe-itinerary/",
    json=flow_a_request
)

print(f"Status: {response_a.status_code}")
print(f"Response: {json.dumps(response_a.json(), indent=2)}")

# Test Flow B: Contextual
print("\n=== Testing Flow B: Contextual ===")
flow_b_request = {
    "flow_type": "contextual",
    "query": "Korean BBQ in Koreatown",
    "location": {
        "lat": 40.7489,
        "lng": -73.9680
    }
}

response_b = requests.post(
    f"{BASE_URL}/generate-vibe-itinerary/",
    json=flow_b_request
)

print(f"Status: {response_b.status_code}")
print(f"Response: {json.dumps(response_b.json(), indent=2)}")
```

### Manual Testing with cURL

**Flow A (Quick Search)**:
```bash
curl -X POST http://localhost:8000/api/generate-vibe-itinerary/ \
  -H "Content-Type: application/json" \
  -d '{
    "flow_type": "quick_search",
    "quick_filter": "Coffee Run"
  }'
```

**Flow B (Contextual)**:
```bash
curl -X POST http://localhost:8000/api/generate-vibe-itinerary/ \
  -H "Content-Type: application/json" \
  -d '{
    "flow_type": "contextual",
    "query": "Korean BBQ",
    "location": {"lat": 40.7489, "lng": -73.9680}
  }'
```

## 📱 Frontend Integration (Next Steps)

### 1. Update ApiService (Flutter)

**File**: `lib/api_service.dart`

Add new method:
```dart
Future<Map<String, dynamic>> generateVibeItinerary({
  required String flowType,
  String? vibeSlug,
  String? quickFilter,
  String? query,
  Map<String, double>? location,
  int maxVenues = 4,
}) async {
  final response = await http.post(
    Uri.parse('$baseUrl/generate-vibe-itinerary/'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'flow_type': flowType,
      if (vibeSlug != null) 'vibe_slug': vibeSlug,
      if (quickFilter != null) 'quick_filter': quickFilter,
      if (query != null) 'query': query,
      if (location != null) 'location': location,
      'max_venues': maxVenues,
    }),
  );
  
  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  } else {
    throw Exception('Failed to generate vibe itinerary');
  }
}
```

### 2. Update PlanditAskAISection

**File**: `lib/widgets/plandit/plandit_ask_ai_section.dart`

Update quick filter button handlers:
```dart
void _handleQuickFilter(String filterName) async {
  setState(() => _isLoading = true);
  
  try {
    final result = await apiService.generateVibeItinerary(
      flowType: 'quick_search',
      quickFilter: filterName,
    );
    
    // Navigate to storyboard
    Navigator.of(context).push(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (context) => PlanditStoryboardView(
          query: filterName,
          itineraryData: result,
          onClose: () => Navigator.of(context).pop(),
        ),
      ),
    );
  } catch (e) {
    print('Error: $e');
  } finally {
    setState(() => _isLoading = false);
  }
}
```

### 3. Update Search Bar Handler

```dart
void _handleSearchSubmit(String query) async {
  final location = await _getCurrentLocation();
  
  setState(() => _isLoading = true);
  
  try {
    final result = await apiService.generateVibeItinerary(
      flowType: 'contextual',
      query: query,
      location: location != null 
        ? {'lat': location.latitude, 'lng': location.longitude}
        : null,
    );
    
    // Navigate to storyboard
    Navigator.of(context).push(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (context) => PlanditStoryboardView(
          query: query,
          itineraryData: result,
          onClose: () => Navigator.of(context).pop(),
        ),
      ),
    );
  } catch (e) {
    print('Error: $e');
  } finally {
    setState(() => _isLoading = false);
  }
}
```

## 📋 Remaining Tasks

### Backend
- [ ] Add `generate_vibe_itinerary` to `views.py`
- [ ] Add import to `urls.py`
- [ ] Add URL pattern to `urls.py`
- [ ] Test with cURL or Postman
- [ ] Verify Supabase `venue_vibes` table has data

### Frontend
- [ ] Add `generateVibeItinerary()` to `ApiService`
- [ ] Update quick filter button handlers in `PlanditAskAISection`
- [ ] Update search bar submit handler
- [ ] Test Flow A (quick filters)
- [ ] Test Flow B (search queries)
- [ ] Handle loading states
- [ ] Handle error states

### Deployment
- [ ] Deploy backend changes to staging
- [ ] Test on staging environment
- [ ] Deploy frontend changes
- [ ] Monitor logs for errors
- [ ] Deploy to production

## 🎯 Success Criteria

- ✅ Clicking "Coffee Run" returns 4 coffee spots in a random NYC neighborhood
- ✅ Searching "Korean BBQ" returns 4 Korean BBQ spots near user location
- ✅ Response time < 2 seconds
- ✅ 90%+ vibe match rate
- ✅ No errors in production logs
