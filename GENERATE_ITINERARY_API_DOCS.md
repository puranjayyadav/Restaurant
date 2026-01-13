# Generate Itinerary API Documentation

## Endpoint
**POST** `{{baseURL}}/api/api/generate-itinerary/`

## Request Body Parameters

### Required Parameters
None - all parameters are optional, but you should provide at least location or query.

### Optional Parameters

#### Location (choose one format)

**Format 1:**
- `start_lat` (float): Starting latitude
- `start_long` (float): Starting longitude

**Format 2 (alternative):**
- `latitude` (float): Starting latitude (alternative to `start_lat`)
- `longitude` (float): Starting longitude (alternative to `start_long`)

**Note:** If no location is provided, the system will use a random NYC location.

#### Vibe & Social Context

- `selected_vibe` (string, optional): Vibe slug to filter venues
  - If not provided, a random vibe will be selected from available vibes in the database
  - See **All Available Vibe Slugs** section below for complete list

- `social_context` (string, optional): Social context for the itinerary
  - Valid values: `"couple"`, `"solo"`, `"group"`, `"family"`
  - Default: `"couple"`

#### Search Parameters

- `radius_meters` (integer, optional): Search radius in meters
  - Default: `3000` (3 km)

- `local_time_start` (string, optional): Starting time for the itinerary
  - Format: `"HH:MM"` (e.g., `"10:00"`, `"14:30"`)
  - Default: `"10:00"`

#### Cuisine Preferences

- `cuisine_preferences` (array of strings, optional): List of vibe slugs to filter by (can include cuisine-based and aesthetic vibes)
  - Examples: `["indian_north", "indian_north_aesthetic"]`, `["korean_pocha_aesthetic"]`, `["thai_isan", "thai_isan_aesthetic"]`
  - See **All Available Vibe Slugs** section below for complete list

- `cuisine_preference_min` (integer, optional): Minimum number of cuisine preferences a venue must match
  - Example: If set to `1`, venue must match at least 1 cuisine from `cuisine_preferences`

- `cuisine_preference_max` (integer, optional): Maximum number of cuisine preferences a venue can match
  - Example: If set to `2`, venue can match at most 2 cuisines from `cuisine_preferences`

## Example Requests

### Example 1: Basic Request
```json
{
  "start_lat": 40.7489,
  "start_long": -73.9680,
  "selected_vibe": "dinner_date",
  "social_context": "couple",
  "radius_meters": 3000,
  "local_time_start": "18:00"
}
```

### Example 2: With Cuisine Preferences (Indian)
```json
{
  "latitude": 40.7489,
  "longitude": -73.9680,
  "selected_vibe": "dinner_date",
  "social_context": "couple",
  "cuisine_preferences": ["indian_north", "indian_north_aesthetic"],
  "radius_meters": 5000,
  "local_time_start": "19:00"
}
```

### Example 3: Work-Friendly Coffee
```json
{
  "start_lat": 40.7230,
  "start_long": -73.9970,
  "selected_vibe": "work_friendly",
  "social_context": "solo",
  "cuisine_preferences": ["coffee", "coffee_run"],
  "radius_meters": 2000,
  "local_time_start": "09:00"
}
```

### Example 4: Korean Pocha Night
```json
{
  "latitude": 40.7489,
  "longitude": -73.9680,
  "selected_vibe": "dinner_group",
  "social_context": "group",
  "cuisine_preferences": ["korean_pocha_aesthetic"],
  "radius_meters": 3000
}
```

### Example 5: Japanese Izakaya Experience
```json
{
  "latitude": 40.7295,
  "longitude": -73.9965,
  "selected_vibe": "late_night_eats",
  "social_context": "group",
  "cuisine_preferences": ["japanese_izakaya_aesthetic", "japanese_sushi_aesthetic"],
  "radius_meters": 2000,
  "local_time_start": "21:00"
}
```

### Example 6: Thai Isan Food
```json
{
  "latitude": 40.7580,
  "longitude": -73.9855,
  "selected_vibe": "casual_lunch",
  "social_context": "couple",
  "cuisine_preferences": ["thai_isan", "thai_isan_aesthetic"],
  "radius_meters": 3000,
  "local_time_start": "12:30"
}
```

### Example 7: Minimal Request (uses defaults)
```json
{
  "start_lat": 40.7489,
  "start_long": -73.9680
}
```

## Response Format

### Success Response (200 OK)
```json
{
  "itinerary": [
    {
      "slot": "coffee",
      "time": "10:00 AM",
      "place_id": "ChIJ...",
      "name": "Coffee Shop Name",
      "address": "123 Main St, New York, NY 10001",
      "latitude": 40.7489,
      "longitude": -73.9680,
      "rating": 4.5,
      "vibe_match": 0.85,
      "walk_time_minutes": 5,
      "duration_from_previous_min": 5
    },
    {
      "slot": "lunch",
      "time": "12:30 PM",
      "place_id": "ChIJ...",
      "name": "Restaurant Name",
      ...
    }
  ],
  "hidden_gems_injected": 2,
  "total_walk_time_mins": 45,
  "narrative": "A curated day exploring the best of the neighborhood..."
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "social_context must be one of: couple, solo, group, family"
}
```

### Error Response (500 Internal Server Error)
```json
{
  "error": "Failed to generate itinerary: <error message>"
}
```

## Response Fields

- `itinerary` (array): List of itinerary stops, each containing:
  - `slot` (string): Time slot name (e.g., "coffee", "lunch", "dinner", "activity")
  - `time` (string): Formatted time (e.g., "10:00 AM")
  - `place_id` (string): Google Maps place ID
  - `name` (string): Venue name
  - `address` (string): Full address
  - `latitude` (float): Venue latitude
  - `longitude` (float): Venue longitude
  - `rating` (float): Venue rating (0-5)
  - `vibe_match` (float): How well venue matches selected vibe (0-1)
  - `walk_time_minutes` (integer): Walking time from previous stop
  - `duration_from_previous_min` (integer): Duration from previous stop

- `hidden_gems_injected` (integer): Number of hidden gem venues added to itinerary
- `total_walk_time_mins` (integer): Total walking time between all stops
- `narrative` (string): Descriptive narrative of the itinerary

## Notes

1. **Location Format**: You can use either `start_lat`/`start_long` OR `latitude`/`longitude` - both are accepted.

2. **Vibe Randomization**: If `selected_vibe` is not provided, the system will randomly select a vibe from available vibes in the database.

3. **Social Context Default**: If `social_context` is not provided, it defaults to `"couple"`.

4. **Cuisine Filtering**: When `cuisine_preferences` are provided, venues are filtered to match those cuisines. The `cuisine_preference_min` and `cuisine_preference_max` parameters allow fine-tuning of how many cuisine matches are required.

5. **Time Slots**: The itinerary is organized into time slots:
   - `coffee` (7-10 AM)
   - `activity` (10-12 PM)
   - `brunch` (12-2 PM)
   - `lunch` (12-3 PM)
   - `afternoon` (2-5 PM)
   - `dinner` (6-9 PM)
   - `nightlife` (9 PM-12 AM)

6. **Quality Filters**: The system automatically filters out:
   - Venues with rating < 4.0
   - Non-restaurant venues (grocery stores, gas stations, etc.)
   - Venues outside the specified radius

---

## All Available Vibe Slugs (49 total)

### Occasion/Activity Vibes
| Slug | Description |
|------|-------------|
| `breakfast_classic` | Classic breakfast spots |
| `brunch_buzzy` | Trendy brunch venues |
| `casual_lunch` | Casual lunch spots |
| `coffee` | Coffee shops |
| `coffee_run` | Quick coffee stops |
| `dinner_date` | Romantic dinner venues |
| `dinner_group` | Group-friendly dinner spots |
| `fine_dining` | Fine dining restaurants |
| `late_night_eats` | Late night food spots |
| `solo_date` | Solo-friendly venues |
| `work_friendly` | Work-friendly cafes |

### Atmosphere/Aesthetic Vibes
| Slug | Description |
|------|-------------|
| `aesthetic` | General aesthetic vibe |
| `art_house` | Art-house atmosphere |
| `dark_academia` | Dark academia aesthetic |
| `minimalist` | Minimalist decor |
| `retro_vintage` | Retro/vintage vibe |
| `urban_jungle` | Plant-filled, urban jungle vibe |

### Bar/Nightlife Vibes
| Slug | Description |
|------|-------------|
| `dive_bar` | Dive bars |
| `listening_bar` | Music-focused bars |
| `natural_wine` | Natural wine bars |
| `rooftop` | Rooftop venues |
| `speakeasy` | Hidden speakeasy bars |

### Cuisine Vibes
| Slug | Aesthetic Version | Description |
|------|-------------------|-------------|
| `caribbean_jamaican` | `caribbean_jamaican_aesthetic` | Jamaican/Caribbean cuisine |
| `colombian` | `colombian_aesthetic` | Colombian cuisine |
| `greek_taverna` | `greek_taverna_aesthetic` | Greek taverna style |
| `indian_north` | `indian_north_aesthetic` | North Indian cuisine |
| `italian_red_sauce` | `italian_red_sauce_aesthetic` | Italian red sauce classics |
| `middle_eastern` | - | Middle Eastern cuisine |
| `pizza_nyc` | - | NYC-style pizza |
| `thai_isan` | `thai_isan_aesthetic` | Thai Isan cuisine |
| - | `chinese_cantonese_aesthetic` | Cantonese aesthetic |
| - | `eastern_european_aesthetic` | Eastern European aesthetic |
| - | `halal_cart_aesthetic` | Halal cart aesthetic |
| - | `japanese_izakaya_aesthetic` | Japanese izakaya aesthetic |
| - | `japanese_sushi_aesthetic` | Japanese sushi aesthetic |
| - | `jewish_deli` | Jewish deli style |
| - | `korean_pocha_aesthetic` | Korean pocha aesthetic |
| - | `peruvian_aesthetic` | Peruvian aesthetic |
| - | `russian_aesthetic` | Russian aesthetic |
| - | `soul_food_aesthetic` | Soul food aesthetic |
| - | `vietnamese_aesthetic` | Vietnamese aesthetic |

### Other Vibes
| Slug | Description |
|------|-------------|
| `bakery_cafe` | Bakery cafes |
| `tea_sanctuary` | Tea-focused venues |

---

### Complete Alphabetical List

```
aesthetic
art_house
bakery_cafe
breakfast_classic
brunch_buzzy
caribbean_jamaican
caribbean_jamaican_aesthetic
casual_lunch
chinese_cantonese_aesthetic
coffee
coffee_run
colombian
colombian_aesthetic
dark_academia
dinner_date
dinner_group
dive_bar
eastern_european_aesthetic
fine_dining
greek_taverna
greek_taverna_aesthetic
halal_cart_aesthetic
indian_north
indian_north_aesthetic
italian_red_sauce
italian_red_sauce_aesthetic
japanese_izakaya_aesthetic
japanese_sushi_aesthetic
jewish_deli
korean_pocha_aesthetic
late_night_eats
listening_bar
middle_eastern
minimalist
natural_wine
peruvian_aesthetic
pizza_nyc
retro_vintage
rooftop
russian_aesthetic
solo_date
soul_food_aesthetic
speakeasy
tea_sanctuary
thai_isan
thai_isan_aesthetic
urban_jungle
vietnamese_aesthetic
work_friendly
```
