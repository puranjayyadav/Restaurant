# Specification: Improve Map Aesthetics

## Goal
Fix a prominent visual glitch (vertical black line) and overhaul the itinerary map for a premium, light-themed aesthetic with clearly numbered stop markers and optimized viewport fitting.

## User Stories
- As a traveler, I want to see a clean, professional map of my itinerary stop points so that I can easily understand my journey at a glance.
- As a foodie, I want the map markers to be clearly numbered in sequence so that I know exactly which stop is which without guessing.
- As a Plandit user, I want the map to automatically zoom to the perfect level so that all my stops are visible as soon as the map loads.

## Specific Requirements

**Fix Visual Glitch (Black Line)**
- Investigate and remove the vertical dark/black line that appears to run "down the map" on the left side (reference `planning/visuals/current_map_issue.png`).
- Check if this is caused by a `VerticalDivider`, a `Border` on the map container, or a misplaced `ListView` separator.

**Consistent Light Theme**
- Ensure the `FlutterMap` uses the CartoDB Positron tile set (`light_all`) for all map instances.
- Remove any dark overlays or gradients that might conflict with the light theme aesthetic.

**Premium Numbered Markers**
- Overhaul the `Marker` child widget in `itinerary_map_view.dart`.
- Markers should be perfectly circular with a clean white background and a subtle elevation (drop shadow).
- Text (stop numbers) should use Plandit's brand typography (configured in `plandit_design_system.dart`) and be high-contrast.
- Use a consistent border color (e.g., `PlanditColors.accent`) to differentiate markers from the map background.

**Intelligent Map Fitting**
- Refine the `_fitMapToBounds` logic in `itinerary_map_view.dart`.
- Use `LatLngBounds` to calculate the envelope of all active chapter locations.
- Ensure `CameraFit.bounds` includes generous padding (e.g., 50-80 pixels) to prevent markers from being cut off by the UI edges or floating buttons.

**Route Visualization**
- Maintain the street-routed polyline functionality using OSRM.
- Adjust the polyline color to a soft, premium tone (e.g., a subtle gold or wheat color) that complements the light map.

## Visual Design

**`planning/visuals/current_map_issue.png`**
- **Problem**: A vertical grey/black line is clearly visible on the left, cutting through the map and itinerary cards.
- **Fix**: Identify the widget causing this overlay and ensure it doesn't bleed into the map viewport.
- **Marker Reference**: The image shows existing numbered circles; these need larger, bolder numbers and better drop shadows to pop against the light map.

## Existing Code to Leverage

**lib/widgets/plandit/itinerary_map_view.dart**
- Re-use the `FlutterMap` setup and `OSRM` routing service logic.
- Refactor the `_fitMapToBounds` method to be more robust.
- Extract the Marker child into a dedicated private method or component for better readability.

**lib/theme/plandit_design_system.dart**
- Re-use `PlanditColors` (accent, foreground) and Google Fonts configurations to ensure marker typography is on-brand.

## Out of Scope
- Implementing a Dark Mode toggle for the map.
- Real-time GPS tracking of the user's current location on the map.
- Draggable markers for manual itinerary re-ordering (this is a separate future feature).
- Custom map tile hosting (stick to CartoDB/OpenStreetMap providers).
