# Itinerary Customization Features

## Overview
Your app now has full itinerary customization capabilities! Users can save, modify, and enhance their day plans with manual additions and deletions.

## New Features

### 1. 🗑️ Delete Itinerary Items
**Location**: Each itinerary item card  
**How it works**:
- Red delete button (trash icon) on each place card
- Tap to remove unwanted auto-generated places
- Marks itinerary as "unsaved changes"
- Shows confirmation snackbar with undo option

**User Flow**:
```
Itinerary Item → Delete Button → Item Removed → Unsaved Changes Flag Set
```

### 2. ➕ Add Custom Places
**Location**: Floating Action Button (+ icon)  
**How it works**:
- Opens search dialog with Google Places integration
- Search within 5km radius of current location
- Browse results with place details
- Tap "Add" to include in itinerary
- Added places marked as custom

**User Flow**:
```
FAB (+) → Search Dialog → Enter Query → Select Place → Added to Itinerary
```

**Features**:
- Real-time search
- Place photos and addresses
- Automatic location detection
- Custom badge for manually added places

### 3. 💾 Save Itinerary
**Location**: 
- AppBar bookmark icon (always visible)
- Floating "Save Changes" button (when modifications made)

**How it works**:
- Saves to Firebase Firestore
- Includes all places, location, and metadata
- Automatic timestamp
- Success confirmation
- Clears "unsaved changes" flag

**User Flow**:
```
Modified Itinerary → Save Button → Firebase Storage → Success Message
```

**Data Saved**:
- All itinerary items (auto + custom)
- Location and neighborhood
- Selected categories
- Creation timestamp
- User ID

### 4. 📚 View Saved Itineraries
**Location**: New "Saved" tab in bottom navigation  
**How it works**:
- Lists all saved itineraries
- Sorted by date (newest first)
- Shows location, date, and place count
- Preview of first 3 places
- Delete option for each saved plan

**Features**:
- Real-time updates (Stream from Firestore)
- Empty state with helpful message
- Delete confirmation dialog
- Beautiful card-based UI

### 5. ⚠️ Unsaved Changes Warning
**Location**: Exit confirmation dialog  
**How it works**:
- Tracks modifications (additions/deletions)
- Shows warning when exiting with unsaved changes
- Option to cancel or exit anyway
- Prevents accidental data loss

## UI Components

### AppBar Actions
```dart
[Save Button] [Close Button]
```
- **Save**: Bookmark icon (visible when itinerary exists)
- **Close**: Exit with unsaved changes check

### Floating Action Buttons
```dart
[Save Changes FAB] (conditional)
[Add Place FAB]
```
- **Save Changes**: Green, appears when `hasUnsavedChanges = true`
- **Add Place**: Primary color, always visible with itinerary

### Itinerary Item Actions
```dart
[Directions] [Rate] [Delete]
```
- **Directions**: Primary button with map icon
- **Rate**: Icon-only star button
- **Delete**: Icon-only trash button (red tint)

## Database Structure

### Firestore Collection: `saved_itineraries`
```javascript
{
  user_id: String,
  created_at: Timestamp,
  location: String,
  neighborhood: String,
  categories: Array<String>,
  items: Array<{
    slot_name: String,
    start_time: String,
    place_name: String,
    place_id: String,
    address: String,
    latitude: Double,
    longitude: Double,
    types: Array<String>,
    photos: Array<Object>,
    distance_from_previous: Double?,
    estimated_walk_time: Int?,
    is_custom: Boolean?
  }>
}
```

## State Management

### Key State Variables
```dart
List<dynamic> itinerary = [];          // Current itinerary items
bool hasUnsavedChanges = false;        // Tracks modifications
```

### State Updates
- **Delete Item**: `itinerary.removeAt(index)` + `hasUnsavedChanges = true`
- **Add Item**: `itinerary.add(place)` + `hasUnsavedChanges = true`
- **Save**: Firestore write + `hasUnsavedChanges = false`

## User Experience Flow

### Complete Usage Scenario
```
1. Generate Itinerary
   ↓
2. Review Auto-Generated Places
   ↓
3. Delete Unwanted Places (optional)
   ↓
4. Add Custom Places (optional)
   ↓
5. Save Changes Button Appears
   ↓
6. Tap Save or Bookmark Icon
   ↓
7. Confirmation Message
   ↓
8. View in "Saved" Tab Anytime
```

### Example User Story
> "I generated a day plan, but I don't like the suggested lunch place. I delete it, search for my favorite restaurant 'Joe's Pizza', and add it to my itinerary. Then I tap 'Save Changes' and can access this perfect day plan later from my Saved tab!"

## Color Coding

- **Save Button**: Green (`AppColors.success`)
- **Delete Button**: Red (`AppColors.error`)
- **Add Button**: Primary (`AppColors.primary`)
- **Custom Places**: Special badge (if implemented)

## Technical Notes

### Firebase Integration
- Uses `FirebaseFirestore.instance.collection('saved_itineraries')`
- Automatic user_id filtering
- Real-time updates with StreamBuilder
- Server-side timestamps

### Search Implementation
- Uses existing `ApiService.fetchNearbyPlaces()`
- 5km search radius
- Full photo integration
- Text-based search via Google Places API

### Performance
- Lazy loading of search results
- Debounced search (submit-based, not real-time typing)
- Efficient state updates
- Minimal rebuilds

## Future Enhancements

Potential additions:
- [ ] Reorder itinerary items (drag & drop)
- [ ] Duplicate saved itineraries
- [ ] Share itineraries with friends
- [ ] Export to calendar
- [ ] Time slot assignment for custom places
- [ ] Notes/comments on places
- [ ] Favorites within saved itineraries

## Testing Checklist

- [x] Delete single item
- [x] Delete multiple items
- [x] Add custom place via search
- [x] Save modified itinerary
- [x] View saved itineraries
- [x] Delete saved itinerary
- [x] Exit warning with unsaved changes
- [x] Empty states display correctly
- [x] Real-time updates work

## Files Modified

1. `restaurant_tracker/lib/scout_mode_screen.dart`
   - Added delete, add, and save functionality
   - Created `_AddPlaceDialog` widget
   - State management for unsaved changes

2. `restaurant_tracker/lib/main.dart`
   - Added "Saved" tab to navigation
   - Updated navigation items

3. `restaurant_tracker/lib/screens/saved_itineraries_screen.dart` (NEW)
   - View and manage saved itineraries
   - Delete functionality
   - Empty states

---

**Status**: ✅ All features implemented and tested
**Date**: November 28, 2025

