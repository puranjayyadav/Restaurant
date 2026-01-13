# Task Breakdown: Improve Map Aesthetics

## Overview
Total Tasks: 12

## Task List

### UI Design & Refinement (Frontend)

#### Task Group 1: Map Styling and Bug Fix
**Dependencies:** None

- [ ] 1.0 Fix map visuals and implement light theme
  - [ ] 1.1 Write 2 focused tests for map viewport sanity
    - Verify map container renders without unexpected overlays
    - Verify initial camera center is within expected bounds
  - [ ] 1.2 Identify and remove the vertical black line glitch
    - Check for `VerticalDivider` or `Border` properties in `ItineraryMapView`
    - Verify sibling widgets in `plandit_storyboard_view.dart` for bleed-through
  - [ ] 1.3 Apply premium light theme tiles
    - Update `urlTemplate` to `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png`
    - Ensure subdomains are correctly set to `['a', 'b', 'c', 'd']`
  - [ ] 1.4 Ensure map layer tests pass

**Acceptance Criteria:**
- No vertical black line is visible on the map
- Map tiles are consistently light-themed (CartoDB Positron)

#### Task Group 2: Marker Overhaul
**Dependencies:** Task Group 1

- [ ] 2.0 Implement premium numbered makers
  - [ ] 2.1 Write 2 focused tests for marker rendering
    - Verify marker count matches stop count
    - Verify markers are positioned correctly at venue coordinates
  - [ ] 2.2 Refactor `Marker` child widget
    - Use `PlanditColors.accent` for borders and high-contrast text
    - Implement circular background with white fill and elevated shadow
    - Use `GoogleFonts.inter` or brand-consistent weight for numbers
  - [ ] 2.3 Optimize marker sizing for legibility
    - Ensure text is centered and clearly readable on mobile
  - [ ] 2.4 Ensure marker layer tests pass

**Acceptance Criteria:**
- Markers clearly show stop numbers (1, 2, 3...)
- Marker design is consistent with Plandit's premium aesthetic
- No markers are cut off at the viewport edge

#### Task Group 3: Intelligent Viewport Management
**Dependencies:** Task Group 2

- [ ] 3.0 Refine auto-zoom and bounds logic
  - [ ] 3.1 Write 2 focused tests for camera fitting
    - Verify all markers are contained within the calculated `LatLngBounds`
    - Verify `CameraFit` applies expected padding
  - [ ] 3.2 Update `_fitMapToBounds` method in `itinerary_map_view.dart`
    - Increase `padding` in `CameraFit.bounds` (aim for 50-80px)
    - Ensure bounds calculation correctly encompasses all active chapters
  - [ ] 3.3 Smooth transition animation
    - Verify `mapController.fitCamera` uses a smooth duration/curve
  - [ ] 3.4 Ensure viewport tests pass

**Acceptance Criteria:**
- All markers are clearly visible upon map load
- Generous padding ensures no markers are hidden behind floating UI elements

## Execution Order

Recommended implementation sequence:
1. Map Styling and Bug Fix (Task Group 1)
2. Marker Overhaul (Task Group 2)
3. Intelligent Viewport Management (Task Group 3)
