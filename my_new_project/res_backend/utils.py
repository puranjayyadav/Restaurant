"""
Utility functions for restaurant matching and enrichment
"""
from .models import ScrapedRestaurant
import math
from django.db.models import Q
from math import radians, cos
from typing import List, Dict, Tuple, Optional, Any

# Try to import fuzzywuzzy, fallback to simple string matching if not available
try:
    from fuzzywuzzy import fuzz
    FUZZYWUZZY_AVAILABLE = True
except ImportError:
    FUZZYWUZZY_AVAILABLE = False
    # Simple fallback function for string similarity
    def _simple_ratio(s1, s2):
        """Simple string similarity ratio (0-100)"""
        s1_lower = s1.lower().strip()
        s2_lower = s2.lower().strip()
        if s1_lower == s2_lower:
            return 100
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 80
        # Count common characters
        common = sum(1 for c in s1_lower if c in s2_lower)
        total = max(len(s1_lower), len(s2_lower))
        return int((common / total) * 100) if total > 0 else 0
    
    # Create a mock fuzz object
    class MockFuzz:
        @staticmethod
        def ratio(s1, s2):
            return _simple_ratio(s1, s2)
    fuzz = MockFuzz()


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on Earth (in meters).
    
    Args:
        lat1, lon1: Latitude and longitude of first point in decimal degrees
        lat2, lon2: Latitude and longitude of second point in decimal degrees
    
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def match_restaurant_with_postgres(google_place):
    """
    Match a Google Places restaurant with a Postgres ScrapedRestaurant entry.
    
    Uses fuzzy name matching and location proximity to find the best match.
    
    Args:
        google_place: Dictionary containing Google Places data with:
            - name: Restaurant name
            - geometry.location.lat: Latitude
            - geometry.location.lng: Longitude
    
    Returns:
        ScrapedRestaurant object if match found, None otherwise
    """
    if not google_place:
        return None
    
    # Extract Google Places data
    place_name = google_place.get('name', '')
    geometry = google_place.get('geometry', {})
    location = geometry.get('location', {})
    place_lat = location.get('lat')
    place_lng = location.get('lng')
    
    if not place_name or not place_lat or not place_lng:
        return None
    
    # Convert to float for calculations
    try:
        place_lat = float(place_lat)
        place_lng = float(place_lng)
    except (ValueError, TypeError):
        return None
    
    # 1. Get all Postgres restaurants within 200m (broader search area)
    # Approximately 0.002 degrees latitude/longitude ≈ 200m at NYC latitude
    lat_range = 0.002
    lng_range = 0.002
    
    nearby_restaurants = ScrapedRestaurant.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        latitude__range=(place_lat - lat_range, place_lat + lat_range),
        longitude__range=(place_lng - lng_range, place_lng + lng_range)
    )
    
    if not nearby_restaurants.exists():
        return None
    
    # 2. Fuzzy match by name and calculate distance
    best_match = None
    best_score = 0
    
    for pg_restaurant in nearby_restaurants:
        # Calculate name similarity (0-100)
        name_score = fuzz.ratio(
            place_name.lower().strip(),
            pg_restaurant.name.lower().strip()
        )
        
        # Calculate distance in meters
        distance_m = haversine_distance(
            place_lat, place_lng,
            float(pg_restaurant.latitude), float(pg_restaurant.longitude)
        )
        
        # Combined score: name similarity (70%) + distance (30%)
        # Distance score: closer = higher (max 100m = 100 points)
        if name_score >= 85 and distance_m <= 100:
            distance_score = max(0, 100 - distance_m)  # 100m = 0 points, 0m = 100 points
            combined_score = name_score * 0.7 + distance_score * 0.3
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = pg_restaurant
    
    return best_match


def enrich_restaurant_data(google_place, postgres_restaurant):
    """
    Enrich Google Places data with Postgres restaurant data.
    
    Args:
        google_place: Dictionary with Google Places data
        postgres_restaurant: ScrapedRestaurant object
    
    Returns:
        Dictionary with merged data
    """
    if not postgres_restaurant:
        return google_place
    
    enriched = google_place.copy()
    
    # Add enrichment flag
    enriched['is_enriched'] = True
    
    # Add Postgres enrichment data
    enriched['postgres_data'] = {
        'menu_items': postgres_restaurant.menu_items if postgres_restaurant.menu_items else [],
        'reviews': postgres_restaurant.raw_data.get('reviews', []) if postgres_restaurant.raw_data else [],
        'tags': postgres_restaurant.raw_data.get('tags', []) if postgres_restaurant.raw_data else [],
        'features': postgres_restaurant.features if postgres_restaurant.features else [],
        'photos': postgres_restaurant.photos if postgres_restaurant.photos else [],
        'about': postgres_restaurant.description or '',
        'price_range': postgres_restaurant.price_range,
        'hours': postgres_restaurant.hours if postgres_restaurant.hours else {},
        'categories': postgres_restaurant.categories if postgres_restaurant.categories else [],
        'phone': postgres_restaurant.phone,
        'website': postgres_restaurant.website,
    }
    
    # Add enrichment metadata
    enriched['enrichment_metadata'] = {
        'has_menu': len(postgres_restaurant.menu_items) > 0 if postgres_restaurant.menu_items else False,
        'has_reviews': len(postgres_restaurant.raw_data.get('reviews', [])) > 0 if postgres_restaurant.raw_data else False,
        'has_tags': len(postgres_restaurant.raw_data.get('tags', [])) > 0 if postgres_restaurant.raw_data else False,
        'data_quality_score': postgres_restaurant.data_quality_score,
    }
    
    return enriched


def query_scraped_restaurants(lat, lng, radius_km, filters=None, require_coordinates=True):
    """
    Query ScrapedRestaurant model with geospatial filtering and optional filters.
    
    Args:
        lat: Center latitude
        lng: Center longitude
        radius_km: Search radius in kilometers
        filters: Dict with optional filters:
            - cuisine: Cuisine type to match
            - price_range: Price range ($, $$, $$$, $$$$)
            - min_rating: Minimum rating (0-5)
            - tags: List of tags to match
            - min_quality_score: Minimum data quality score
        require_coordinates: If False, return restaurants without coordinates (for city/state matching)
    
    Returns:
        List of ScrapedRestaurant objects sorted by score
    """
    if filters is None:
        filters = {}
    
    # Start with base query
    if require_coordinates:
        queryset = ScrapedRestaurant.objects.filter(
            is_active=True,
            duplicate_of__isnull=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
    else:
        queryset = ScrapedRestaurant.objects.filter(
            is_active=True,
            duplicate_of__isnull=True
        )
    
    # Geospatial filtering using bounding box (faster than haversine for all records)
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * cos(radians(lat)))
    
    queryset = queryset.filter(
        latitude__gte=lat - lat_delta,
        latitude__lte=lat + lat_delta,
        longitude__gte=lng - lon_delta,
        longitude__lte=lng + lon_delta
    )
    
    # Apply filters
    if filters.get('cuisine'):
        cuisine = filters['cuisine'].lower()
        # Create cuisine variations for better matching
        cuisine_variations = [cuisine]
        cuisine_mapping = {
            'italian': ['italian', 'italy', 'pasta', 'pizza', 'trattoria', 'ristorante'],
            'french': ['french', 'france', 'bistro', 'brasserie', 'cafe'],
            'mexican': ['mexican', 'mexico', 'taco', 'burrito', 'tex-mex'],
            'japanese': ['japanese', 'japan', 'sushi', 'ramen', 'izakaya'],
            'chinese': ['chinese', 'china', 'dim sum', 'szechuan', 'cantonese'],
            'thai': ['thai', 'thailand', 'pad thai'],
            'indian': ['indian', 'india', 'curry', 'tandoor'],
            'mediterranean': ['mediterranean', 'greek', 'turkish', 'lebanese', 'middle eastern'],
            'american': ['american', 'burger', 'bbq', 'steakhouse', 'diner'],
            'korean': ['korean', 'korea', 'bbq', 'korean bbq'],
            'spanish': ['spanish', 'spain', 'tapas', 'paella'],
            'greek': ['greek', 'greece', 'gyro'],
        }
        if cuisine in cuisine_mapping:
            cuisine_variations = cuisine_mapping[cuisine]
        
        # Build query with all variations
        cuisine_filter = Q()
        for variation in cuisine_variations:
            cuisine_filter |= (
                Q(categories__icontains=variation) |
                Q(name__icontains=variation) |
                Q(description__icontains=variation) |
                Q(raw_data__cuisine__icontains=variation)
            )
        queryset = queryset.filter(cuisine_filter)
    
    if filters.get('price_range'):
        price_range = filters['price_range']
        # Map price ranges to database values
        price_mapping = {
            '$30 and under': ['$', '$$'],
            '$31-$50': ['$$$'],
            '$50+': ['$$$$', '$$$$$']
        }
        if price_range in price_mapping:
            queryset = queryset.filter(price_range__in=price_mapping[price_range])
    
    if filters.get('min_rating'):
        queryset = queryset.filter(rating__gte=float(filters['min_rating']))
    
    if filters.get('min_quality_score'):
        queryset = queryset.filter(data_quality_score__gte=int(filters['min_quality_score']))
    
    if filters.get('tags'):
        tags = filters['tags']
        if isinstance(tags, str):
            tags = [tags]
        tag_filter = Q()
        for tag in tags:
            tag_filter |= Q(raw_data__tags__icontains=tag) | Q(features__icontains=tag)
        queryset = queryset.filter(tag_filter)
    
    # Get all restaurants and calculate exact distances
    restaurants = list(queryset)
    
    # Filter by exact haversine distance and add distance
    results = []
    for restaurant in restaurants:
        if restaurant.latitude and restaurant.longitude:
            distance_m = haversine_distance(
                lat, lng,
                float(restaurant.latitude),
                float(restaurant.longitude)
            )
            distance_km = distance_m / 1000.0
            
            if distance_km <= radius_km:
                restaurant.distance_km = distance_km
                results.append(restaurant)
        elif not require_coordinates:
            # If coordinates not required, include restaurant but mark distance as unknown
            restaurant.distance_km = None
            results.append(restaurant)
    
    return results


def calculate_restaurant_score(restaurant, filters=None, user_preferences=None):
    """
    Calculate a score for a restaurant based on quality, rating, filter match, and user preferences.
    
    Args:
        restaurant: ScrapedRestaurant object or dict with place data
        filters: Optional dict with filters (for match bonus)
        user_preferences: Optional dict with user preferences:
            - preferred_cuisines: List of preferred cuisine types
            - price_sensitivity: 'low', 'medium', 'high'
            - preferred_tags: List of preferred tags
    
    Returns:
        Score (0-100) for use as OR-Tools penalty
    """
    score = 0
    
    # Handle both ScrapedRestaurant objects and dicts (from Google Places)
    if isinstance(restaurant, dict):
        # Google Places data format
        rating = restaurant.get('rating') or 0
        rating = float(rating) if rating else 0
        
        # Handle None values for user_ratings_total
        total_reviews_raw = restaurant.get('user_ratings_total')
        total_reviews = int(total_reviews_raw) if total_reviews_raw is not None else 0
        
        categories = restaurant.get('types', [])
        price_level = restaurant.get('price_level', -1)
        name = restaurant.get('name', '')
        description = restaurant.get('description', '') or ''
        photos = restaurant.get('photos', [])
        data_quality_score = 50  # Default for Google Places data
    else:
        # ScrapedRestaurant object
        rating = float(restaurant.rating) if restaurant.rating else 0
        total_reviews = int(restaurant.total_reviews) if restaurant.total_reviews is not None else 0
        categories = restaurant.categories or []
        price_level = -1  # Will use price_range instead
        name = restaurant.name
        description = restaurant.description or ''
        photos = restaurant.photos or []
        data_quality_score = restaurant.data_quality_score if restaurant.data_quality_score is not None else 50
    
    # Base quality (40 points)
    # Ensure data_quality_score is a number
    data_quality_score = float(data_quality_score) if data_quality_score is not None else 50.0
    score += data_quality_score * 0.4
    
    # Rating (30 points)
    if rating:
        score += (float(rating) / 5.0) * 30
    
    # Review count (10 points)
    if total_reviews > 100:
        score += 10
    elif total_reviews > 50:
        score += 5
    elif total_reviews > 20:
        score += 2
    
    # Data richness (20 points)
    if isinstance(restaurant, dict):
        # Google Places format
        if photos and len(photos) > 0:
            score += 5
        if description:
            score += 5
        # Assume some data richness for Google Places
        score += 10
    else:
        # ScrapedRestaurant format
        if restaurant.menu_items and len(restaurant.menu_items) > 0:
            score += 5
        if photos and len(photos) > 0:
            score += 5
        if restaurant.raw_data and restaurant.raw_data.get('reviews'):
            score += 5
        if description:
            score += 5
    
    # User preference bonus (up to 20 points)
    if user_preferences:
        # Preferred cuisine match (+20 points)
        if user_preferences.get('preferred_cuisines'):
            preferred = [c.lower() for c in user_preferences['preferred_cuisines']]
            categories_lower = [c.lower() for c in categories]
            name_lower = name.lower()
            desc_lower = description.lower()
            
            for cuisine in preferred:
                if (cuisine in name_lower or
                    any(cuisine in cat for cat in categories_lower) or
                    cuisine in desc_lower):
                    score += 20
                    break
        
        # Preferred tag match (+10 points)
        if user_preferences.get('preferred_tags'):
            preferred_tags = [t.lower() for t in user_preferences['preferred_tags']]
            if isinstance(restaurant, dict):
                # Check in types/categories
                for tag in preferred_tags:
                    if any(tag in str(c).lower() for c in categories):
                        score += 10
                        break
            else:
                restaurant_tags = restaurant.raw_data.get('tags', []) if restaurant.raw_data else []
                restaurant_features = restaurant.features or []
                for tag in preferred_tags:
                    if (any(tag in str(t).lower() for t in restaurant_tags) or
                        any(tag in str(f).lower() for f in restaurant_features)):
                        score += 10
                        break
    
    # Filter match bonus (optional)
    if filters:
        # Cuisine match
        if filters.get('cuisine'):
            cuisine = filters['cuisine'].lower()
            categories_lower = [c.lower() for c in categories]
            if (cuisine in name.lower() or
                any(cuisine in cat for cat in categories_lower) or
                cuisine in description.lower()):
                score += 10
        
        # Price match
        if filters.get('price_range'):
            price_range = filters['price_range']
            price_mapping = {
                '$30 and under': ['$', '$$'],
                '$31-$50': ['$$$'],
                '$50+': ['$$$$', '$$$$$']
            }
            if price_range in price_mapping:
                if isinstance(restaurant, dict):
                    # Google Places uses price_level (0-4)
                    if price_range == '$30 and under' and price_level in [0, 1]:
                        score += 10
                    elif price_range == '$31-$50' and price_level == 2:
                        score += 10
                    elif price_range == '$50+' and price_level in [3, 4]:
                        score += 10
                else:
                    if restaurant.price_range in price_mapping[price_range]:
                        score += 10
        
        # Tag match
        if filters.get('tags'):
            tags = filters['tags']
            if isinstance(tags, str):
                tags = [tags]
            if isinstance(restaurant, dict):
                for tag in tags:
                    tag_lower = tag.lower()
                    if any(tag_lower in str(c).lower() for c in categories):
                        score += 10
                        break
            else:
                restaurant_tags = restaurant.raw_data.get('tags', []) if restaurant.raw_data else []
                restaurant_features = restaurant.features or []
                for tag in tags:
                    tag_lower = tag.lower()
                    if (any(tag_lower in str(t).lower() for t in restaurant_tags) or
                        any(tag_lower in str(f).lower() for f in restaurant_features)):
                        score += 10
                        break
    
    return min(100, score)  # Cap at 100


def calculate_visit_duration(place, category=None):
    """
    Calculate estimated visit duration for a place based on its category.
    
    Args:
        place: Place dict with 'types' or ScrapedRestaurant object with 'categories'
        category: Optional explicit category override
    
    Returns:
        Duration in minutes
    """
    # Get category from place
    if category:
        category_lower = category.lower()
    elif isinstance(place, dict):
        types = place.get('types', [])
        category_lower = types[0].lower() if types else ''
    else:
        # ScrapedRestaurant object
        categories = place.categories or []
        category_lower = categories[0].lower() if categories else ''
    
    # Category to duration mapping
    duration_map = {
        'restaurant': 90,
        'food': 90,
        'meal_takeaway': 30,
        'cafe': 45,
        'bakery': 30,
        'bar': 60,
        'night_club': 120,
        'lounge': 60,
        'museum': 120,
        'art_gallery': 90,
        'park': 60,
        'shopping_mall': 90,
        'store': 45,
        'library': 60,
    }
    
    # Check for matches
    for cat_key, duration in duration_map.items():
        if cat_key in category_lower:
            return duration
    
    # Default duration
    return 60


def get_time_windows_for_categories(categories=None, solver_data=None):
    """
    Get time window for a place based on its categories.
    
    Args:
        categories: List of category strings (e.g., ['restaurant', 'food'])
                   If None, returns the full category mapping dict
    
    Returns:
        If categories provided: (min_start, max_start) tuple in minutes from 00:00
        If None: (category_windows_dict, time_slot_windows_dict) tuple
    """
    # Time windows in minutes from 00:00
    windows = {
        'morning': (540, 660),      # 09:00-11:00
        'mid_day': (660, 840),      # 11:00-14:00
        'afternoon': (840, 1020),   # 14:00-17:00
        'evening': (1020, 1200),    # 17:00-20:00
    }
    
    # Map category types to allowed time windows
    category_windows = {
        # Morning categories
        'cafe': [windows['morning'], windows['afternoon']],
        'bakery': [windows['morning'], windows['afternoon']],
        'breakfast': [windows['morning']],
        
        # Mid-day categories
        'restaurant': [windows['mid_day'], windows['evening']],
        'food': [windows['mid_day'], windows['evening']],
        'meal_takeaway': [windows['mid_day'], windows['evening']],
        
        # Afternoon categories
        'museum': [windows['afternoon']],
        'art_gallery': [windows['afternoon']],
        'park': [windows['afternoon']],
        'shopping_mall': [windows['afternoon']],
        'store': [windows['afternoon']],
        
        # Evening categories
        'bar': [windows['evening']],
        'night_club': [windows['evening']],
        'lounge': [windows['evening']],
    }
    
    # If solver_data has explicit time_bias, prefer that
    if solver_data and isinstance(solver_data, dict):
        bias = str(solver_data.get('time_bias') or '').strip().lower()
        if bias:
            if bias == 'morning':
                return windows['morning']
            if bias in ('mid-day', 'mid_day', 'afternoon'):
                # Treat generic daytime / afternoon as afternoon window
                return windows['afternoon']
            if bias in ('evening', 'sunset', 'dinner'):
                return windows['evening']
            if bias in ('late night', 'late-night', 'late'):
                # Late night still treated as evening window for now
                return windows['evening']

        # Fallback: if category_normalized is present, treat it as a single-category hint
        cat_norm = solver_data.get('category_normalized')
        if cat_norm and not categories:
            categories = [cat_norm]

    # If categories provided, return a single time window tuple
    if categories:
        categories_lower = [c.lower() if isinstance(c, str) else str(c).lower() for c in categories]
        
        # Find first matching category
        for cat in categories_lower:
            for cat_key, windows_list in category_windows.items():
                if cat_key in cat:
                    # Return the first (earliest) window
                    return windows_list[0]
        
        # Default to mid_day if no match
        return windows['mid_day']
    
    # Return full mapping if no categories provided
    return category_windows, windows


def ensure_diversity(restaurants, max_same_cuisine=2, max_same_price=3):
    """
    Enforce diversity constraints on restaurant list.
    
    Args:
        restaurants: List of ScrapedRestaurant objects (should be sorted by score)
        max_same_cuisine: Maximum restaurants with same cuisine
        max_same_price: Maximum restaurants with same price range
    
    Returns:
        Filtered list with diversity enforced
    """
    if not restaurants:
        return []
    
    selected = []
    cuisine_count = {}
    price_count = {}
    
    for restaurant in restaurants:
        # Get cuisine (from categories or name)
        cuisine = None
        if restaurant.categories:
            cuisine = restaurant.categories[0] if isinstance(restaurant.categories, list) else None
        if not cuisine:
            # Try to extract from name
            name_lower = restaurant.name.lower()
            common_cuisines = ['italian', 'french', 'mexican', 'japanese', 'chinese', 
                             'thai', 'indian', 'mediterranean', 'american', 'korean']
            for c in common_cuisines:
                if c in name_lower:
                    cuisine = c
                    break
        
        # Check cuisine diversity
        if cuisine:
            if cuisine_count.get(cuisine, 0) >= max_same_cuisine:
                continue
            cuisine_count[cuisine] = cuisine_count.get(cuisine, 0) + 1
        
        # Check price diversity
        price = restaurant.price_range
        if price:
            if price_count.get(price, 0) >= max_same_price:
                continue
            price_count[price] = price_count.get(price, 0) + 1
        
        selected.append(restaurant)
    
    return selected


def calculate_route_distance(restaurants):
    """
    Calculate total walking distance for a route of restaurants.
    
    Args:
        restaurants: List of ScrapedRestaurant objects with latitude/longitude
    
    Returns:
        Total distance in kilometers
    """
    if len(restaurants) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(len(restaurants) - 1):
        r1 = restaurants[i]
        r2 = restaurants[i + 1]
        
        if r1.latitude and r1.longitude and r2.latitude and r2.longitude:
            distance_m = haversine_distance(
                float(r1.latitude), float(r1.longitude),
                float(r2.latitude), float(r2.longitude)
            )
            total_distance += distance_m / 1000.0  # Convert to km
    
    return total_distance


def optimize_route(restaurants, center_lat, center_lng, max_distance_between=1.0):
    """
    Optimize restaurant route using nearest neighbor algorithm.
    
    Args:
        restaurants: List of ScrapedRestaurant objects
        center_lat: Starting point latitude
        center_lng: Starting point longitude
        max_distance_between: Maximum distance between consecutive restaurants (km)
    
    Returns:
        Ordered list of restaurants forming optimal route
    """
    if not restaurants:
        return []
    
    if len(restaurants) == 1:
        return restaurants
    
    # Start with restaurant closest to center
    unvisited = restaurants.copy()
    route = []
    current_lat = center_lat
    current_lng = center_lng
    
    while unvisited:
        # Find nearest unvisited restaurant
        nearest = None
        nearest_distance = float('inf')
        
        for restaurant in unvisited:
            if restaurant.latitude and restaurant.longitude:
                distance_m = haversine_distance(
                    current_lat, current_lng,
                    float(restaurant.latitude), float(restaurant.longitude)
                )
                distance_km = distance_m / 1000.0
                
                # Check if within max distance constraint
                if distance_km <= max_distance_between and distance_km < nearest_distance:
                    nearest = restaurant
                    nearest_distance = distance_km
        
        # If no restaurant within constraint, pick closest anyway
        if nearest is None:
            for restaurant in unvisited:
                if restaurant.latitude and restaurant.longitude:
                    distance_m = haversine_distance(
                        current_lat, current_lng,
                        float(restaurant.latitude), float(restaurant.longitude)
                    )
                    distance_km = distance_m / 1000.0
                    if distance_km < nearest_distance:
                        nearest = restaurant
                        nearest_distance = distance_km
        
        if nearest:
            route.append(nearest)
            unvisited.remove(nearest)
            current_lat = float(nearest.latitude)
            current_lng = float(nearest.longitude)
        else:
            # No more reachable restaurants
            break
    
    return route


# ============================================================================
# Directional Search (Cone of Interest) Functions
# ============================================================================

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing (direction) from point 1 to point 2 in degrees.
    
    Args:
        lat1, lon1: Starting point coordinates
        lat2, lon2: Destination point coordinates
    
    Returns:
        Bearing in degrees (0-360, where 0 = North, 90 = East, 180 = South, 270 = West)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    y = math.sin(delta_lon) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))
    
    bearing = math.atan2(y, x)
    bearing_degrees = math.degrees(bearing)
    
    # Normalize to 0-360
    return (bearing_degrees + 360) % 360


def is_in_forward_cone(user_lat: float, user_lon: float, heading: float, 
                       place_lat: float, place_lon: float, cone_angle: int = 120) -> bool:
    """
    Check if a place is within the forward cone of the user's heading.
    
    Args:
        user_lat, user_lon: User's current location
        heading: User's heading in degrees (0-360, North=0)
        place_lat, place_lon: Place coordinates to check
        cone_angle: Cone angle in degrees (default 120 = 60° on each side)
    
    Returns:
        True if place is in forward cone, False otherwise
    """
    # Calculate bearing from user to place
    bearing_to_place = calculate_bearing(user_lat, user_lon, place_lat, place_lon)
    
    # Calculate angular difference
    angle_diff = abs(bearing_to_place - heading)
    
    # Handle wrap-around (e.g., heading=350, bearing=10 should be 20°, not 340°)
    if angle_diff > 180:
        angle_diff = 360 - angle_diff
    
    # Check if within cone (half angle on each side)
    half_cone = cone_angle / 2.0
    return angle_diff <= half_cone


def filter_directional_places(places: List[Dict], user_location: Tuple[float, float], 
                              heading: Optional[float], cone_angle: int = 120) -> List[Dict]:
    """
    Filter places to only those in the forward cone of user's heading.
    
    Args:
        places: List of place dictionaries with 'lat'/'lng' or 'geometry.location.lat'/'lng'
        user_location: (lat, lon) tuple of user's location
        heading: User's heading in degrees (None to skip filtering)
        cone_angle: Cone angle in degrees (default 120)
    
    Returns:
        Filtered list of places within forward cone, sorted by forward distance
    """
    if heading is None:
        return places
    
    user_lat, user_lon = user_location
    filtered = []
    
    for place in places:
        # Extract coordinates
        if 'lat' in place and 'lng' in place:
            place_lat = float(place['lat'])
            place_lon = float(place['lng'])
        elif 'geometry' in place and 'location' in place['geometry']:
            place_lat = float(place['geometry']['location']['lat'])
            place_lon = float(place['geometry']['location']['lng'])
        else:
            continue  # Skip places without coordinates
        
        if is_in_forward_cone(user_lat, user_lon, heading, place_lat, place_lon, cone_angle):
            # Calculate forward distance (projection along heading direction)
            bearing_to_place = calculate_bearing(user_lat, user_lon, place_lat, place_lon)
            angle_diff = abs(bearing_to_place - heading)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            # Calculate actual distance
            distance_m = haversine_distance(user_lat, user_lon, place_lat, place_lon)
            
            # Forward distance = distance * cos(angle_diff) - penalize places off heading
            forward_distance = distance_m * math.cos(math.radians(angle_diff))
            
            # Add forward_distance to place for sorting
            place_copy = place.copy()
            place_copy['_forward_distance'] = forward_distance
            place_copy['_bearing'] = bearing_to_place
            filtered.append(place_copy)
    
    # Sort by forward distance (closer along heading = better)
    filtered.sort(key=lambda p: p.get('_forward_distance', float('inf')))
    
    return filtered


# ============================================================================
# Time-Context Query Filter Functions
# ============================================================================

def get_time_context_query(current_hour: int) -> List[str]:
    """
    Get query keywords based on current time of day.
    
    Args:
        current_hour: Current hour (0-23)
    
    Returns:
        List of query keywords for scraping
    """
    if 8 <= current_hour < 11:
        # Morning: 8:00 AM - 11:00 AM
        return ["coffee", "breakfast", "cafe", "bakery", "park"]
    elif 11 <= current_hour < 12:
        # Late morning: 11:00 AM - 12:00 PM
        return ["brunch", "cafe", "restaurant"]
    elif 12 <= current_hour < 14:
        # Lunch: 12:00 PM - 2:00 PM
        return ["lunch", "restaurant", "fast casual", "food"]
    elif 14 <= current_hour < 17:
        # Afternoon: 2:00 PM - 5:00 PM
        return ["museum", "art_gallery", "park", "shopping_mall", "cafe"]
    elif 17 <= current_hour < 21:
        # Dinner: 5:00 PM - 9:00 PM
        return ["restaurant", "dinner", "bar", "lounge"]
    else:
        # Late night: 9:00 PM+
        return ["bar", "night_club", "late night food", "dessert"]


def get_time_context_label(current_hour: int) -> str:
    """
    Get human-readable time context label.
    
    Args:
        current_hour: Current hour (0-23)
    
    Returns:
        Time context label (e.g., "morning", "lunch", "dinner")
    """
    if 8 <= current_hour < 11:
        return "morning"
    elif 11 <= current_hour < 12:
        return "brunch"
    elif 12 <= current_hour < 14:
        return "lunch"
    elif 14 <= current_hour < 17:
        return "afternoon"
    elif 17 <= current_hour < 21:
        return "dinner"
    else:
        return "late_night"


def apply_time_context_filter(places: List[Dict], current_hour: int) -> List[Dict]:
    """
    Filter places based on time context relevance.
    
    This is a soft filter - prioritizes places that match time context,
    but doesn't exclude others completely.
    
    Args:
        places: List of place dictionaries
        current_hour: Current hour (0-23)
    
    Returns:
        Filtered and re-sorted list (time-relevant places first)
    """
    time_context = get_time_context_label(current_hour)
    context_keywords = get_time_context_query(current_hour)
    
    scored_places = []
    
    for place in places:
        # Extract place types/categories
        place_types = []
        if 'types' in place:
            place_types = [t.lower() for t in place.get('types', [])]
        elif 'categories' in place:
            place_types = [c.lower() for c in place.get('categories', [])]
        
        # Check if place matches time context
        match_score = 0
        for keyword in context_keywords:
            keyword_lower = keyword.lower()
            if any(keyword_lower in pt for pt in place_types):
                match_score += 1
        
        # Add score to place
        place_copy = place.copy()
        place_copy['_time_match_score'] = match_score
        scored_places.append(place_copy)
    
    # Sort by time match score (higher = more relevant)
    scored_places.sort(key=lambda p: p.get('_time_match_score', 0), reverse=True)
    
    return scored_places

