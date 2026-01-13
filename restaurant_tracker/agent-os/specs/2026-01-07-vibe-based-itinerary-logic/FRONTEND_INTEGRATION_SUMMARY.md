# Frontend Integration Summary

This document summarizes the changes made to the Flutter frontend to integrate with the new Vibe-Based Itinerary Backend.

## 1. ApiService (`lib/api_service.dart`)

Added `generateVibeItinerary` method to handle API calls to the new endpoint.

```dart
  /// Generate vibe-based itinerary (Flow A & Flow B)
  Future<Map<String, dynamic>> generateVibeItinerary({
    required String flowType,
    String? vibeSlug,
    String? quickFilter,
    String? query,
    Map<String, double>? location,
    int maxVenues = 4,
  }) async {
    // ... implementation ...
  }
```

## 2. PlanditAskAISection (`lib/widgets/plandit/plandit_ask_ai_section.dart`)

Updated to support:
- **Flow A (Quick Search)**: Clicking a quick filter (e.g., "Coffee Run") now triggers a location-agnostic, vibe-centric search producing a random neighborhood itinerary.
- **Flow B (Contextual Search)**: Typing in the search bar (e.g., "Korean BBQ in Koreatown") triggers a contextual search using the device's current location (if available) or parsing the query.
- **Helper Methods**: Added `_getCurrentLocation`, `_handleQuickFilter`, `_showLoadingDialog`, `_navigateToStoryboard`.
- **Imports**: Added `package:geolocator/geolocator.dart`.

## 3. Data Models (`lib/widgets/plandit/storyboard_models.dart`)

Updated `VenueVariant.fromJson` to accept `description` field from the API response as a fallback for the AI note/reason.

```dart
    // Support 'notes' or 'reason' or 'description'
    final reason = json['reason'] ?? json['notes'] ?? json['description'] ?? 'A great spot for your itinerary';
```

## 4. Storyboard View (`lib/widgets/plandit/plandit_storyboard_view.dart`)

Updated `_parseApiChapters` to handle the `photos` list returned by the backend (Supabase) if `image_url` is not expressly provided.

```dart
      // Use venue image or fallback to Unsplash
      String? imageUrl = venue['image_url'];
      if (imageUrl == null && venue['photos'] != null && (venue['photos'] as List).isNotEmpty) {
         imageUrl = (venue['photos'] as List).first.toString();
      }
      final image = imageUrl ?? _getDefaultImage(category);
```

## Next Steps for User

1.  **Run the App**: `flutter run`
2.  **Test Flow A**: Tap on "Coffee Run" or "Date Night" in the horizontal list.
    *   *Expectation*: Loading dialog -> Itinerary generated for a random popular neighborhood (e.g., Astoria, DUMBO).
3.  **Test Flow B**: Type "Sushi in SoHo" and tap "Go".
    *   *Expectation*: Loading dialog -> Itinerary generated for SoHo with correct venues.
4.  **Permissions**: Ensure the app has Location permissions enabled for Flow B to work optimally.
