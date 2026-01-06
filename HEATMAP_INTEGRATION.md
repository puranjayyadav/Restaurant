# Density Heatmap - Flutter Integration Complete! 🎉

## Files Created

1. **`lib/services/density_heatmap_service.dart`** - Service for fetching heatmap data from backend
2. **`lib/widgets/density_heatmap_widget.dart`** - Reusable heatmap widget with filters
3. **`lib/screens/density_heatmap_screen.dart`** - Standalone screen for testing

---

## Quick Start

### Option 1: Add to Existing Navigation

Add a button to navigate to the heatmap screen:

```dart
// In your existing screen (e.g., trip_wizard_screen.dart)
import 'package:restaurant_tracker/screens/density_heatmap_screen.dart';

// Add a navigation button
ElevatedButton.icon(
  onPressed: () {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => DensityHeatmapScreen(
          baseUrl: 'http://YOUR_SERVER_IP:8000',
        ),
      ),
    );
  },
  icon: Icon(Icons.map),
  label: Text('Explore Density Map'),
)
```

### Option 2: Embed in Trip Wizard

Add the widget directly to your trip wizard:

```dart
// In trip_wizard_screen.dart
import 'package:restaurant_tracker/widgets/density_heatmap_widget.dart';

// In your build method
Container(
  height: 400,  // Set a fixed height
  child: DensityHeatmapWidget(
    center: LatLng(40.7216, -74.0047),  // Use user's location
    baseUrl: 'http://YOUR_SERVER_IP:8000',
    onCellTap: (cellId, placeCount) {
      // Handle tap - maybe show places in that cell
      print('User tapped zone with $placeCount places');
    },
  ),
)
```

---

## Configuration

### Update Server URL

In `density_heatmap_screen.dart`, line 9:
```dart
this.baseUrl = 'http://YOUR_IP:8000',  // ← Change this
```

Or pass it dynamically:
```dart
DensityHeatmapScreen(
  baseUrl: 'http://192.168.1.163:8000',  // Your Django server IP
)
```

### Customize Grid Size

In `density_heatmap_widget.dart`, line 48-49:
```dart
gridSize: 0.008,  // Smaller = more detailed (slower)
gridCount: 11,    // More cells = larger area covered
```

**Recommendations:**
- **Detailed view**: `gridSize: 0.005, gridCount: 15` (225 cells)
- **Fast/overview**: `gridSize: 0.01, gridCount: 9` (81 cells)
- **Default (balanced)**: `gridSize: 0.008, gridCount: 11` (121 cells)

---

## Features

### ✅ Vibe Filtering

Five filter options:
- **All** - Show all places
- **Coffee** - Coffee shops and cafes
- **Nightlife** - Clubs and lounges
- **Dining** - Restaurants
- **Bars** - Bars and pubs

### ✅ Interactive Polygons

- **Tap a zone** → Bottom sheet shows:
  - Density score (0-100)
  - Number of places
  - Average rating
  - "Explore Places" button

### ✅ Color-Coded Density

- **Deep Red (#D32F2F)** - 80-100: Maximum density
- **Orange-Red (#FF5722)** - 60-80: High density
- **Orange (#FF9800)** - 40-60: Medium density
- **Light Orange (#FFA726)** - 20-40: Low-medium
- **Green (#81C784)** - 0-20: Low density

---

## Testing

### 1. Run your Django server

```bash
cd c:\Users\PURANJAY\OneDrive\Documents\Res_2\my_new_project
python manage.py runserver 0.0.0.0:8000
```

### 2. Update the IP in Flutter code

Find your computer's local IP and update `baseUrl` in the code.

### 3. Run the Flutter app

```bash
cd c:\Users\PURANJAY\OneDrive\Documents\Res_2\restaurant_tracker
flutter run
```

### 4. Navigate to the heatmap screen

Use the navigation example above to test the screen.

---

## Troubleshooting

### "Failed to load heatmap: 404"
- Check that Django server is running on `0.0.0.0:8000`
- Verify the URL path: `/api/neighborhoods/density/`
- Check `res_backend/urls.py` has the route registered

### "Network error"
- Verify your phone and computer are on the same WiFi
- Check firewall isn't blocking port 8000
- Test the API in browser: `http://YOUR_IP:8000/api/neighborhoods/density/?lat=40.7216&lng=-74.0047`

### Polygons not showing
- Check console for errors
- Verify GeoJSON is being returned (check network tab)
- Make sure `flutter_map` and `latlong2` are in `pubspec.yaml`

---

## Next Steps

1. **Location Integration**: Use user's current location instead of hardcoded SoHo
2. **Place List**: Implement the "Explore Places" button to show actual places
3. **Cache Results**: Cache heatmap data to avoid repeated API calls
4. **Save Favorites**: Let users save favorite density zones
5. **Sharing**: Share interesting density discoveries

---

## API Reference

### Endpoint
```
GET /api/neighborhoods/density/
```

### Query Parameters
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `lat` | float | ✅ | - | Center latitude |
| `lng` | float | ✅ | - | Center longitude |
| `vibe` | string | ❌ | - | Filter by vibe ('coffee', 'nightlife') |
| `category` | string | ❌ | - | Filter by category ('restaurant', 'bar') |
| `min_rating` | float | ❌ | - | Minimum rating filter |
| `grid_size` | float | ❌ | 0.01 | Cell size in degrees |
| `grid_count` | int | ❌ | 15 | Cells in each direction |

---

Enjoy exploring your city's density hotspots! 🗺️✨
