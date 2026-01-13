# Postman Testing Guide for Hybrid Search API

## Endpoint Details

**URL:** `http://localhost:8000/api/api/hybrid-search/` (Local)  
**Production:** `https://your-render-app.onrender.com/api/api/hybrid-search/`

**Method:** `POST`

**Headers:**
```
Content-Type: application/json
```

## Request Body Format

```json
{
  "query": "romantic Indian dinner",
  "location": {
    "lat": 40.7489,
    "lng": -73.9680
  },
  "radius_km": 3.0,
  "limit": 20
}
```

### Parameters

- **`query`** (required): Natural language search query
- **`location`** (optional): Object with `lat` and `lng` for proximity filtering
- **`radius_km`** (optional, default: 3.0): Search radius in kilometers
- **`limit`** (optional, default: 20): Maximum number of results to return

## Example Requests

### 1. Romantic Indian Dinner

```json
{
  "query": "romantic Indian dinner",
  "location": {
    "lat": 40.7489,
    "lng": -73.9680
  },
  "radius_km": 5.0,
  "limit": 10
}
```

### 2. Work Friendly Coffee

```json
{
  "query": "work friendly coffee in SoHo",
  "location": {
    "lat": 40.7230,
    "lng": -73.9970
  },
  "radius_km": 3.0,
  "limit": 10
}
```

### 3. Korean BBQ

```json
{
  "query": "Korean BBQ",
  "location": {
    "lat": 40.7489,
    "lng": -73.9680
  },
  "radius_km": 5.0,
  "limit": 10
}
```

### 4. Date Night Sushi

```json
{
  "query": "date night sushi",
  "location": {
    "lat": 40.7489,
    "lng": -73.9680
  },
  "radius_km": 3.0,
  "limit": 10
}
```

### 5. Simple Query (No Location)

```json
{
  "query": "best pizza in NYC",
  "limit": 20
}
```

## Expected Response Format

```json
{
  "query": "romantic Indian dinner",
  "parsed_params": {
    "selected_vibe": "dinner_date",
    "cuisine_preferences": ["indian_north", "indian_south"],
    "social_context": "couple",
    "location_hint": null,
    "time_preference": "dinner",
    "parsed_intent": "romantic Indian dinner"
  },
  "results_count": 10,
  "results": [
    {
      "place_id": "ChIJ...",
      "name": "Restaurant Name",
      "address": "123 Main St, New York, NY 10001",
      "latitude": 40.7489,
      "longitude": -73.9680,
      "rating": 4.6,
      "review_count": 150,
      "semantic_score": 0.393,
      "vibe_match_score": 1.0,
      "insight_score": 0.45,
      "final_score": 0.553,
      "matched_vibes": ["dinner_date", "italian_red_sauce"],
      "display_hook": "Truffle Dreaming 🍄",
      "must_order": {
        "items": ["Truffle Pasta", "Wine Pairing"]
      }
    }
  ]
}
```

## Step-by-Step Postman Setup

### 1. Create New Request
- Click **New** → **HTTP Request**
- Name it: "Hybrid Search - Romantic Indian Dinner"

### 2. Set Method and URL
- Method: **POST**
- URL: `http://localhost:8000/api/api/hybrid-search/`

### 3. Add Headers
- Go to **Headers** tab
- Add:
  - Key: `Content-Type`
  - Value: `application/json`

### 4. Add Request Body
- Go to **Body** tab
- Select **raw**
- Select **JSON** from dropdown
- Paste one of the example JSON requests above

### 5. Send Request
- Click **Send**
- Check the response in the bottom panel

## Response Fields Explained

- **`semantic_score`**: Similarity score from embedding search (0.0 - 1.0)
- **`vibe_match_score`**: How well the venue matches requested vibes (0.0 - 1.0)
- **`insight_score`**: Bonus points from AI insights (can be negative for traps)
- **`final_score`**: Weighted combination (60% semantic + 25% vibe + 15% insights)
- **`matched_vibes`**: Array of vibe slugs that matched
- **`display_hook`**: Editorial hook/description (may contain emojis)
- **`must_order`**: Recommended items from AI insights

## Common Locations for Testing

### NYC Locations
```json
{
  "lat": 40.7489,  // Midtown Manhattan
  "lng": -73.9680
}
```

```json
{
  "lat": 40.7230,  // SoHo
  "lng": -73.9970
}
```

```json
{
  "lat": 40.6782,  // Brooklyn
  "lng": -73.9442
}
```

## Troubleshooting

### 500 Internal Server Error
- Check if Django server is running
- Check server logs for error details
- Verify Supabase credentials are set

### Empty Results
- Try increasing `radius_km`
- Try removing `location` to search all venues
- Check if embeddings have been generated for venues

### Timeout Errors
- Reduce `limit` parameter
- Increase `radius_km` might help (more venues to choose from)
- Check Supabase connection

## Testing Different Scenarios

### Test Semantic Search
Use queries that rely on meaning, not exact keywords:
```json
{
  "query": "cozy place for a first date",
  "limit": 10
}
```

### Test Vibe Matching
Use queries that should match specific vibes:
```json
{
  "query": "romantic dinner",
  "limit": 10
}
```

### Test Cuisine Preferences
```json
{
  "query": "authentic Korean food",
  "limit": 10
}
```

### Test Combined Query
```json
{
  "query": "romantic Italian restaurant with good wine",
  "location": {
    "lat": 40.7489,
    "lng": -73.9680
  },
  "radius_km": 5.0,
  "limit": 15
}
```
