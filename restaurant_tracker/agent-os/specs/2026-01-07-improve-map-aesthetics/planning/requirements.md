# Requirements: Improve Map Aesthetics

## Feature Description
Improve the visual quality and usability of the itinerary map view in the Flutter application.

## High-Level Goals
- Fix a prominent visual glitch (black line down the map).
- Transition the map style to a premium "Light Theme".
- Enhance markers to show clear, numbered stop points (e.g., 1, 2, 3...).
- Improve map viewport management to automatically zoom/pan so all itinerary points are visible.

## Specific Requirements
- **Bug Fix**: Eliminate the vertical black/dark line that currently appears on the map overlay (see visuals).
- **Map Theme**: Apply a clean, light-colored map style that aligns with Plandit's lifestyle aesthetic.
- **Marker Overhaul**:
    - Replace generic pins with numbered circles/labels indicating the stop sequence.
    - Ensure stop 1, stop 2, etc., are clearly legible.
- **Auto-Zoom & Clipping**: 
    - Calculate the bounding box for all current itinerary markers.
    - Animate the camera view to fit these markers with appropriate padding so no marker is clipped at the edges.

## Visual Context
A screenshot has been provided showing the "black line" issue and the current state of numbered markers (which need a cleaner, more marked design).
