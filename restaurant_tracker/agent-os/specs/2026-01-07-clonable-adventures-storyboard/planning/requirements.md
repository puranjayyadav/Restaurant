# Requirements: Cloneable Adventures in Storyboard

## Data Structure
The `cloneable_adventures` table in Supabase contains:
- `source_id`: Unique identifier (URL)
- `title`: Original title
- `new_title`: Curated title for display
- `subtitle`: Short description
- `tags`: Array of tags
- `score`: Quality score
- `stops`: Array of stop objects with:
  - `place_name`: Name of the venue
  - `notes`: Description/reason for inclusion
  - `category`: Type of venue (Nightlife, Food, etc.)
  - `solver_data`: Metadata for itinerary solver
  - `search_query`: Query to find the place
- `header_image_url`: Featured image
- `original_url`: Source URL

## User Flow
1. User sees "The NYC Edit" section on the dashboard
2. User taps on any collection card
3. App navigates to `PlanditStoryboardView` with the adventure data
4. Storyboard displays the stops as chapters with map, timeline, and details
5. User can save the itinerary or explore individual venues

## Technical Constraints
- The `stops` array must be compatible with `VenueVariant.fromJson()`
- Map markers require lat/lng coordinates (currently missing in some stops)
- The "Regenerate" button should be hidden or disabled for static adventures
- Vibe tuner shows the same stops across all variants (no dynamic variants)

## Success Criteria
- Tapping a NYC Edit card opens the storyboard view
- All stops display correctly with names, descriptions, and categories
- Map shows markers for stops (where coordinates are available)
- Save functionality works for cloneable adventures
- No crashes or visual glitches
