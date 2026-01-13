# Requirements: Vibe-Based Itinerary Logic

## Business Requirements

### User Experience Goals
1. **Instant Discovery**: Quick filter buttons should provide immediate, curated results without requiring location input
2. **Contextual Relevance**: Search bar queries should respect user location and intent
3. **Vibe Consistency**: Results should strongly align with the selected vibe (90%+ match rate)
4. **Performance**: Response time must be under 2 seconds for both flows

### Functional Requirements

#### Flow A: Quick Search
- **Trigger**: User clicks one of 5 filter buttons (Coffee Run, Work Friendly, Breakfast Classic, Brunch Spot, Date Night)
- **Location**: Randomly selected NYC neighborhood (ignores user location)
- **Results**: Exactly 4 venues matching the vibe
- **Diversity**: Results should be from the same neighborhood but different venues
- **Repeatability**: Clicking the same button multiple times should show different neighborhoods

#### Flow B: Contextual Search
- **Trigger**: User types query in search bar or uses advanced filters
- **Location**: User's specified location OR current geolocation
- **Results**: Up to 4 venues matching detected vibe
- **Proximity**: Results within 3km radius of user location
- **Fallback**: If < 4 venues found, expand radius to 5km

## Technical Requirements

### Data Structure

#### venue_vibes Table Schema
```sql
CREATE TABLE venue_vibes (
  id UUID PRIMARY KEY,
  place_id TEXT NOT NULL,
  vibe_slug TEXT NOT NULL,
  confidence_score FLOAT,
  created_at TIMESTAMP,
  FOREIGN KEY (place_id) REFERENCES places(place_id)
);

CREATE INDEX idx_venue_vibes_slug ON venue_vibes(vibe_slug);
CREATE INDEX idx_venue_vibes_place ON venue_vibes(place_id);
```

#### Vibe Slug Categories
- **Occasion**: `casual_lunch`, `dinner_date`, `brunch_buzzy`, `fine_dining`
- **Time**: `breakfast_classic`, `late_night_eats`, `coffee_run`
- **Cuisine**: `korean_bbq`, `japanese_izakaya`, `italian_red_sauce`, `chinese_sichuan`
- **Aesthetic**: `minimalist`, `dark_academia`, `retro_vintage`, `urban_jungle`
- **Venue Type**: `dive_bar`, `speakeasy`, `rooftop`, `listening_bar`

### API Contract

#### Request Format (Flow A - Quick Search)
```json
{
  "flow_type": "quick_search",
  "quick_filter": "Coffee Run",
  "vibe_slug": "coffee_run"
}
```

#### Request Format (Flow B - Contextual)
```json
{
  "flow_type": "contextual",
  "query": "Korean BBQ in Koreatown",
  "location": {
    "lat": 40.7489,
    "lng": -73.9680
  },
  "vibe_slug": "korean_bbq"
}
```

#### Response Format
```json
{
  "itinerary": [
    {
      "name": "Devoción",
      "category": "Coffee Shop",
      "vibe_slug": "coffee_run",
      "lat": 40.7489,
      "lng": -73.9680,
      "reason": "Specialty Colombian coffee in a light-filled space"
    }
  ],
  "metadata": {
    "flow_type": "quick_search",
    "neighborhood": "Williamsburg",
    "vibe_match_rate": 1.0
  }
}
```

### Performance Requirements
- **Query Time**: < 500ms for database query
- **Total Response Time**: < 2 seconds end-to-end
- **Concurrent Users**: Support 100 concurrent requests
- **Cache Strategy**: Cache popular vibe queries for 1 hour

### Error Handling
- **No Venues Found**: Return helpful message suggesting nearby vibes
- **Invalid Vibe Slug**: Fall back to general search
- **Location Unavailable**: Default to Manhattan center (40.7589, -73.9851)
- **API Timeout**: Return cached results if available

## Data Requirements

### NYC Neighborhoods List
Must include at least these 15 neighborhoods with coordinates:
1. West Village (40.7358, -74.0036)
2. Williamsburg (40.7081, -73.9571)
3. Astoria (40.7644, -73.9235)
4. SoHo (40.7233, -74.0030)
5. East Village (40.7264, -73.9818)
6. DUMBO (40.7033, -73.9888)
7. Park Slope (40.6710, -73.9778)
8. Greenpoint (40.7304, -73.9511)
9. Lower East Side (40.7153, -73.9874)
10. Nolita (40.7227, -73.9956)
11. Chelsea (40.7465, -74.0014)
12. Flatiron (40.7411, -73.9897)
13. Tribeca (40.7163, -74.0086)
14. Bushwick (40.6942, -73.9210)
15. Bed-Stuy (40.6872, -73.9418)

### Vibe Slug Mapping
Quick filter buttons must map to these exact slugs:
- "Coffee Run" → `coffee_run`
- "Work Friendly" → `work_friendly`
- "Breakfast Classic" → `breakfast_classic`
- "Brunch Spot" → `brunch_buzzy`
- "Date Night" → `dinner_date`

### Fuzzy Matching Rules
User query → vibe_slug detection:
- "Korean BBQ" → `korean_bbq`
- "Italian" → `italian_red_sauce` OR `italian_regional`
- "Coffee" → `coffee_run` OR `coffee`
- "Brunch" → `brunch_buzzy`
- "Date night" → `dinner_date`
- "Speakeasy" → `speakeasy`

## Security & Privacy
- **Location Data**: Never store user location permanently
- **Query Logging**: Log queries for analytics but anonymize user IDs
- **Rate Limiting**: 60 requests per minute per user
- **API Authentication**: Require valid API key for all requests

## Testing Requirements
- **Unit Tests**: 90%+ code coverage
- **Integration Tests**: Test both flows end-to-end
- **Load Tests**: Verify performance under 100 concurrent users
- **A/B Testing**: Compare vibe-based vs. traditional search satisfaction

## Success Metrics
- **Vibe Match Rate**: 90%+ of results match intended vibe
- **User Satisfaction**: 4+ star rating on vibe-based results
- **Click-Through Rate**: 60%+ of users click on at least one venue
- **Repeat Usage**: 40%+ of users use quick filters multiple times per session
