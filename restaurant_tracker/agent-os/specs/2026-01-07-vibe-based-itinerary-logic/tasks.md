# Tasks: Vibe-Based Itinerary Logic

## Backend Tasks (Python/FastAPI)

### Core Infrastructure
- [ ] Create `vibe_mapper.py` service
  - [ ] Define `QUICK_FILTER_MAP` dictionary (5 filter buttons → vibe_slug)
  - [ ] Implement `parse_query_to_vibe()` function for fuzzy matching
  - [ ] Create `get_all_vibe_slugs()` helper returning the 91 available vibes
  
- [ ] Create `nyc_neighborhoods.py` service
  - [ ] Define `NYC_NEIGHBORHOODS` list with ~15 popular areas + coordinates
  - [ ] Implement `get_random_neighborhood()` function
  - [ ] Add `get_neighborhood_bounds()` for bounding box queries

### Database Layer
- [ ] Update Supabase queries in `supabase_client.py`
  - [ ] Add `query_venues_by_vibe(vibe_slug, location, radius)` function
  - [ ] Optimize query with proper indexes on `venue_vibes.vibe_slug`
  - [ ] Add `get_vibe_venue_count(vibe_slug)` for validation

### API Endpoints
- [ ] Update `/api/generate-itinerary/` endpoint
  - [ ] Add `flow_type` parameter (enum: "quick_search" | "contextual")
  - [ ] Add `vibe_slug` parameter (optional string)
  - [ ] Add `quick_filter` parameter (optional string for button name)
  
- [ ] Update `itinerary_solver.py`
  - [ ] Implement Flow A logic (quick search with random neighborhood)
  - [ ] Implement Flow B logic (contextual with user location)
  - [ ] Add vibe-based venue filtering
  - [ ] Ensure max 4 venues per vibe in results

### Testing
- [ ] Write unit tests for `vibe_mapper.py`
  - [ ] Test all 5 quick filter mappings
  - [ ] Test fuzzy matching ("Korean BBQ" → `korean_bbq`)
  - [ ] Test edge cases (unknown vibes, typos)
  
- [ ] Write integration tests for itinerary generation
  - [ ] Test Flow A with each of the 5 quick filters
  - [ ] Test Flow B with various cuisine queries
  - [ ] Verify location randomization in Flow A
  - [ ] Verify location adherence in Flow B

## Frontend Tasks (Flutter)

### UI Components
- [ ] Update `PlanditAskAISection` widget
  - [ ] Modify quick filter button handlers
  - [ ] Pass `flow_type: "quick_search"` to API
  - [ ] Pass `quick_filter` parameter with button name
  - [ ] Remove location from request for quick filters

- [ ] Update search bar submission logic
  - [ ] Pass `flow_type: "contextual"` to API
  - [ ] Include user's current location in request
  - [ ] Add location permission handling if needed

- [ ] Update `PlanditFilterSheet`
  - [ ] Map cuisine selections to `vibe_slug` values
  - [ ] Create `CUISINE_TO_VIBE_MAP` constant
  - [ ] Pass selected vibe to API as `contextual` flow

### API Service
- [ ] Update `ApiService.generateItineraryFromQuery()`
  - [ ] Add `flowType` parameter
  - [ ] Add `vibeSlug` parameter
  - [ ] Add `quickFilter` parameter
  - [ ] Update request body structure

### Data Models
- [ ] Create `VibeFilter` model
  - [ ] Define enum for quick filter types
  - [ ] Define mapping to vibe_slug values
  - [ ] Add helper methods for conversion

## Documentation
- [ ] Create API documentation
  - [ ] Document new endpoint parameters
  - [ ] Provide example requests for both flows
  - [ ] List all 91 available vibe_slug values
  
- [ ] Update frontend documentation
  - [ ] Document quick filter button behavior
  - [ ] Document search bar vibe detection
  - [ ] Add troubleshooting guide for vibe matching

## Data & Configuration
- [ ] Verify `venue_vibes` table structure in Supabase
  - [ ] Confirm all 91 vibe_slugs exist
  - [ ] Verify gem_count accuracy
  - [ ] Check for missing venue associations
  
- [ ] Create configuration file
  - [ ] Define NYC neighborhood list with coordinates
  - [ ] Set default search radius (3km)
  - [ ] Configure max venues per vibe (4)

## Deployment
- [ ] Deploy backend changes
  - [ ] Run database migrations if needed
  - [ ] Update environment variables
  - [ ] Deploy to staging for testing
  
- [ ] Deploy frontend changes
  - [ ] Update API endpoint URLs if changed
  - [ ] Test on iOS and Android
  - [ ] Deploy to production

## Monitoring & Analytics
- [ ] Add logging for vibe detection
  - [ ] Log which vibe_slug is matched for each query
  - [ ] Track Flow A vs Flow B usage
  - [ ] Monitor vibe match success rate
  
- [ ] Add analytics events
  - [ ] Track quick filter button clicks
  - [ ] Track vibe-based search queries
  - [ ] Monitor user satisfaction with results
