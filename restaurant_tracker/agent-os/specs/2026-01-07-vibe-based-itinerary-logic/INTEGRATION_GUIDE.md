# Manual Integration Steps

## ✅ Step 1: Add Endpoint to views.py

**File**: `my_new_project/res_backend/views.py`

**Action**: Add the following code at the **end of the file** (after line 3821):

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
        
        print(f"[generate_vibe_itinerary] Flow: {flow_type}, Vibe: {vibe_slug}, Filter: {quick_filter}, Query: {query}")
        
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
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        import traceback
        print(f"[generate_vibe_itinerary] Error: {str(e)}")
        print(f"[generate_vibe_itinerary] Traceback: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to generate vibe itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

**Quick Copy**: The code is also available in `endpoint_code.py` in this directory.

---

## ✅ Step 2: Update urls.py Imports

**File**: `my_new_project/res_backend/urls.py`

**Action**: Update line 14 to include `generate_vibe_itinerary`:

**BEFORE**:
```python
from .views import (
    verify_token, get_trips, EstablishmentViewSet, get_trip_recommendations, 
    get_similar_restaurants, record_user_interaction, create_session, 
    get_personalized_recommendations, generate_day_itinerary,
    submit_public_itinerary, get_public_itineraries, like_public_itinerary,
    add_public_itinerary_to_schedule, share_public_itinerary, update_public_itinerary,
    delete_public_itinerary, approve_public_itinerary, get_user_stats,
    get_scraped_restaurants, get_scraped_restaurant_detail, create_scraped_restaurant,
    generate_and_enrich_itinerary, get_pre_created_itineraries, 
    pre_create_itineraries, get_featured_itineraries, get_pre_created_itinerary_detail,
    next_best_action, create_itinerary_skeleton, get_address_suggestions_view,
    get_hotspot_itinerary, generate_itinerary_view, get_itinerary_details_view,
    parse_query_view
)
```

**AFTER** (add `generate_vibe_itinerary` at the end):
```python
from .views import (
    verify_token, get_trips, EstablishmentViewSet, get_trip_recommendations, 
    get_similar_restaurants, record_user_interaction, create_session, 
    get_personalized_recommendations, generate_day_itinerary,
    submit_public_itinerary, get_public_itineraries, like_public_itinerary,
    add_public_itinerary_to_schedule, share_public_itinerary, update_public_itinerary,
    delete_public_itinerary, approve_public_itinerary, get_user_stats,
    get_scraped_restaurants, get_scraped_restaurant_detail, create_scraped_restaurant,
    generate_and_enrich_itinerary, get_pre_created_itineraries, 
    pre_create_itineraries, get_featured_itineraries, get_pre_created_itinerary_detail,
    next_best_action, create_itinerary_skeleton, get_address_suggestions_view,
    get_hotspot_itinerary, generate_itinerary_view, get_itinerary_details_view,
    parse_query_view, generate_vibe_itinerary
)
```

---

## ✅ Step 3: Add URL Pattern

**File**: `my_new_project/res_backend/urls.py`

**Action**: Add the following line to `urlpatterns` (after line 67):

```python
urlpatterns = [
    # ... existing patterns ...
    path('generate-vibe-itinerary/', generate_vibe_itinerary, name='generate-vibe-itinerary'),
]
```

**Full context** (lines 65-68):
```python
    path('generate-itinerary/', generate_itinerary_view, name='generate-itinerary'),
    path('parse-query/', parse_query_view, name='parse-query'),
    path('itinerary-details/', get_itinerary_details_view, name='itinerary-details'),
    path('generate-vibe-itinerary/', generate_vibe_itinerary, name='generate-vibe-itinerary'),  # ADD THIS LINE
]
```

---

## ✅ Step 4: Test the Backend

### Option A: Using cURL

**Test Flow A (Quick Search)**:
```bash
curl -X POST http://localhost:8000/api/generate-vibe-itinerary/ \
  -H "Content-Type: application/json" \
  -d "{\"flow_type\": \"quick_search\", \"quick_filter\": \"Coffee Run\"}"
```

**Test Flow B (Contextual)**:
```bash
curl -X POST http://localhost:8000/api/generate-vibe-itinerary/ \
  -H "Content-Type: application/json" \
  -d "{\"flow_type\": \"contextual\", \"query\": \"Korean BBQ\", \"location\": {\"lat\": 40.7489, \"lng\": -73.9680}}"
```

### Option B: Using Python

Create `test_vibe_api.py`:
```python
import requests
import json

BASE_URL = "http://localhost:8000/api"

# Test Flow A
print("=== Testing Flow A ===")
response = requests.post(
    f"{BASE_URL}/generate-vibe-itinerary/",
    json={"flow_type": "quick_search", "quick_filter": "Coffee Run"}
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))

# Test Flow B
print("\n=== Testing Flow B ===")
response = requests.post(
    f"{BASE_URL}/generate-vibe-itinerary/",
    json={
        "flow_type": "contextual",
        "query": "Korean BBQ",
        "location": {"lat": 40.7489, "lng": -73.9680}
    }
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
```

Run with:
```bash
python test_vibe_api.py
```

---

## ✅ Step 5: Verify Supabase Data

Make sure your Supabase `venue_vibes` table has data:

```sql
-- Check total venues with vibes
SELECT COUNT(*) FROM venue_vibes;

-- Check coffee_run vibe specifically
SELECT COUNT(*) FROM venue_vibes WHERE vibe_slug = 'coffee_run';

-- Check all vibe counts
SELECT vibe_slug, COUNT(*) as count 
FROM venue_vibes 
GROUP BY vibe_slug 
ORDER BY count DESC 
LIMIT 20;
```

---

## 🎯 Expected Results

### Flow A Response:
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
      "photos": []
    }
    // ... 3 more venues
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

### Flow B Response:
```json
{
  "itinerary": [
    {
      "slot": 1,
      "name": "Kang Ho Dong Baekjeong",
      "category": "Korean BBQ",
      "lat": 40.7489,
      "lng": -73.9680,
      "reason": "A great korean bbq spot",
      "rating": 4.5,
      "price_range": "$$$",
      "place_id": "ChIJ...",
      "vibe_slug": "korean_bbq",
      "photos": []
    }
    // ... 3 more venues
  ],
  "metadata": {
    "flow_type": "contextual",
    "vibe_slug": "korean_bbq",
    "user_location": {"lat": 40.7489, "lng": -73.9680},
    "vibe_match_rate": 1.0,
    "total_venues": 4,
    "query": "Korean BBQ"
  }
}
```

---

## 🐛 Troubleshooting

### Error: "No module named 'vibe_itinerary_solver'"
- **Solution**: Make sure `vibe_itinerary_solver.py` is in `res_backend/` directory
- **Check**: Run `ls res_backend/vibe_*` to verify files exist

### Error: "No module named 'vibe_mapper'"
- **Solution**: Make sure `vibe_mapper.py` and `nyc_neighborhoods.py` exist
- **Check**: All three files should be in the same directory

### Error: "get_venues_from_supabase() missing"
- **Solution**: This function should already exist in `geohash_cache.py`
- **Check**: Search for `def get_venues_from_supabase` in `geohash_cache.py`

### Empty Results
- **Solution**: Check if `venue_vibes` table has data in Supabase
- **Check**: Run the SQL queries in Step 5

### Import Errors
- **Solution**: Restart Django server after adding new files
- **Command**: `python manage.py runserver`

---

## ✅ Checklist

- [ ] Added `generate_vibe_itinerary()` function to `views.py`
- [ ] Updated imports in `urls.py`
- [ ] Added URL pattern in `urls.py`
- [ ] Restarted Django server
- [ ] Tested Flow A with cURL or Python
- [ ] Tested Flow B with cURL or Python
- [ ] Verified Supabase has venue_vibes data
- [ ] Checked server logs for errors

---

## 🚀 Next: Frontend Integration

Once backend is working, proceed to frontend integration:
- See `IMPLEMENTATION_SUMMARY.md` for Flutter code
- Update `ApiService` in `lib/api_service.dart`
- Update quick filter handlers in `PlanditAskAISection`
- Update search bar handler

---

## 📞 Need Help?

If you encounter issues:
1. Check Django server logs for detailed error messages
2. Verify all three Python files exist: `vibe_mapper.py`, `nyc_neighborhoods.py`, `vibe_itinerary_solver.py`
3. Ensure Supabase credentials are configured
4. Test with simple cURL commands first before complex queries
