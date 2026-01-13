# Specification: Display Cloneable Adventures in Storyboard Format

## Goal
When a user clicks on an itinerary card in "The NYC Edit" (cloneable adventures) or other featured sections, it should open in the same premium `PlanditStoryboardView` used for AI-generated itineraries, rather than a static detail page.

## User Stories
- As a user, I want to explore curated NYC adventures with the same cinematic experience as my AI-generated plans.
* As a traveler, I want to see the map, timeline, and vibe details for a featured itinerary just by tapping on it.

## Technical Requirements

### 1. Unified Itinerary Data Model
Ensure that data fetched from `cloneable_adventures` can be seamlessly converted or passed to `PlanditStoryboardView`.
- **Transformation**: `cloneable_adventures.stops` should mapped to the `itinerary` key expected by `PlanditStoryboardView`.
- **Field Mapping**:
  - `new_title` or `title` -> `query` (as the display title).
  - `stops` -> `itinerary` list.

### 2. Interaction in Curated Sections
Update `PlanditCuratedCategories` to handle taps on collection cards.
- Add `onTap` to `_CollectionCard`.
- Pass the full adventure data to the tap handler.
- Navigate to `PlanditStoryboardView` using the selected adventure data.

### 3. Handle Static vs dynamic itinerary
Since cloneable adventures are "pre-solved", the `VibeTuner` and "Regenerate" buttons should either:
- Be hidden for static adventures.
- Or simply mirror the same data across all "vibe" variants (which is what `_parseApiChapters` already does if there are no variants provided).

## Out of Scope
- Creating new cloneable adventures from within the app.
- Editing existing cloneable adventures.
