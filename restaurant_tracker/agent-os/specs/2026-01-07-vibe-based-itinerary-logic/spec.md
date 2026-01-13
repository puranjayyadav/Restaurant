# Specification: Vibe-Based Itinerary Logic

## Goal
Implement intelligent vibe-based filtering for the itinerary generation API, supporting two distinct user flows: **Quick Search** (randomized NYC neighborhoods) and **Ask AI** (location-aware contextual search). This will leverage the `venue_vibes` table to match user preferences with curated venue collections.

## User Stories
- As a user clicking "Coffee Run", I want to discover 4 great coffee spots in a random trendy NYC neighborhood without specifying my location.
- As a user typing "Korean BBQ in Koreatown" in the search bar, I want results centered around my specified location with venues matching that vibe.
- As a developer, I want a clear separation between quick-filter logic and contextual AI search logic to maintain code clarity.

## Specific Requirements

### **Flow A: Quick Search (Standard Filters)**
Triggered when the user clicks one of the 5 filter buttons below the search bar.

#### Filter Button Mappings
```
"Coffee Run" → vibe_slug: coffee_run (1605 venues)
"Work Friendly" → vibe_slug: work_friendly (1755 venues)
"Breakfast Classic" → vibe_slug: breakfast_classic (1314 venues)
"Brunch Spot" → vibe_slug: brunch_buzzy (1082 venues)
"Date Night" → vibe_slug: dinner_date (999 venues)
```

#### Behavior Rules
1. **Location Handling**: IGNORE user's current geolocation
2. **Randomization**: Randomly select from a curated list of popular NYC neighborhoods:
   - West Village, Williamsburg, Astoria, SoHo, East Village, DUMBO, Park Slope, Greenpoint, LES, Nolita, Chelsea, Flatiron, Tribeca
3. **Venue Selection**: 
   - Query `venue_vibes` table WHERE `vibe_slug = <mapped_slug>`
   - Filter results to the randomly selected neighborhood
   - Return maximum 4 venues
4. **Priority**: 100% of results must match the selected vibe

### **Flow B: Ask AI (Contextual Search)**
Triggered when the user types a query in the main search bar or uses advanced filters.

#### Behavior Rules
1. **Location Handling**: STRICTLY use:
   - User's explicitly provided location (if specified in query), OR
   - User's current geolocation (if available), OR
   - Default to Manhattan center if neither available
2. **Vibe Matching**:
   - Parse user query for cuisine/vibe keywords
   - Match to available `vibe_slug` values (see data source list)
   - Support fuzzy matching (e.g., "Korean BBQ" → `korean_bbq`, "Italian" → `italian_regional` or `italian_red_sauce`)
3. **Venue Selection**:
   - Query `venue_vibes` table WHERE `vibe_slug = <matched_slug>`
   - Filter by proximity to user's location (radius: 3km default)
   - Return maximum 4 venues matching the vibe
4. **Priority**: Majority (75%+) of results should match the detected vibe

### **Data Source: venue_vibes Table**
The backend must query the `venue_vibes` table with the following structure:
- `vibe_slug` (string): The vibe identifier
- `place_id` (string): Reference to the venue
- Additional venue metadata (name, lat, lng, category, etc.)

**Available Vibe Slugs** (91 total):
- Top vibes by count: `casual_lunch` (2108), `solo_date` (2083), `late_night_eats` (1847)
- Cuisine-specific: `korean_bbq`, `japanese_izakaya`, `italian_red_sauce`, `chinese_sichuan`, etc.
- Aesthetic vibes: `minimalist`, `dark_academia`, `retro_vintage`, `urban_jungle`
- Occasion vibes: `fine_dining`, `dive_bar`, `speakeasy`, `rooftop`

## Technical Implementation

### Backend (Python/FastAPI)
1. **New Endpoint Parameter**: Add `flow_type` parameter to `/api/generate-itinerary/`
   - Values: `"quick_search"` or `"contextual"`
2. **Vibe Mapping Service**: Create `vibe_mapper.py` with:
   - Dictionary mapping UI filter names to `vibe_slug` values
   - Fuzzy matching function for user queries
3. **Location Randomizer**: Create `nyc_neighborhoods.py` with:
   - List of 15-20 popular NYC neighborhoods with coordinates
   - Random selection function
4. **Query Builder**: Update `itinerary_solver.py` to:
   - Accept `vibe_slug` parameter
   - Query `venue_vibes` table via Supabase
   - Apply location filtering based on flow type

### Frontend (Flutter)
1. **Quick Filter Buttons**: Update `PlanditAskAISection` to:
   - Pass `flow_type: "quick_search"` when filter buttons are clicked
   - Pass mapped `vibe_slug` to API
2. **Search Bar**: Update to:
   - Pass `flow_type: "contextual"` for manual queries
   - Include user's location in API request
3. **Filter Sheet**: Update `PlanditFilterSheet` to:
   - Map selected cuisines to `vibe_slug` values
   - Pass as `contextual` flow

## Out of Scope
- Multi-vibe mixing (e.g., "Coffee + Brunch" in one query)
- User-created custom vibes
- Time-of-day automatic vibe selection
- Vibe popularity trending/analytics

## Success Criteria
- Clicking "Coffee Run" returns 4 coffee spots in a random NYC neighborhood
- Searching "Korean BBQ in Koreatown" returns 4 Korean BBQ spots near Koreatown
- 90%+ of results match the intended vibe
- Response time < 2 seconds for both flows
