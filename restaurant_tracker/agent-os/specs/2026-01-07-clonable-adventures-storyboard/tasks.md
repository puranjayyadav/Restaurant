# Tasks: Cloneable Adventures in Storyboard

## Frontend Tasks

### PlanditCuratedCategories
- [x] Add `GestureDetector` to `_CollectionCard`.
- [x] Pass the raw adventure `Map<String, dynamic>` to a callback or handle navigation internally.
- [x] Implement transition to `PlanditStoryboardView` on tap.

### PlanditStoryboardView
- [x] Ensure `PlanditStoryboardView` handles cases where `itineraryData` might be already in the "legacy" format (with `stops` instead of `itinerary`).
- [ ] Optional: Add a flag `isStatic` to hide/disable the "Regenerate" button for curated edits.

## Integration & Data
- [x] Verify the structure of `stops` in `cloneable_adventures` table matches the venue format needed for `VenueVariant.fromJson()`.
- [ ] Check if `source_id` from curated adventures can be used for deep-linking if needed.

## Testing
- [ ] Verify that tapping a "NYC Edit" card opens a functional storyboard.
- [ ] Ensure map markers and polylines load for the static stops.
- [ ] Check that the "Save" functionality still works for curated plans.
