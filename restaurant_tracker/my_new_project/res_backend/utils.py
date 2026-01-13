"""
Utility functions for restaurant matching and enrichment
"""
from .models import ScrapedRestaurant
import math
from django.db.models import Q
from math import radians, cos
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

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

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the bearing in degrees from point 1 to point 2.
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lon = lon2_rad - lon1_rad

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - (math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))

    initial_bearing = math.atan2(x, y)

    # Convert to degrees and normalize to 0-360
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

def is_in_forward_cone(
    user_lat: float, 
    user_lon: float, 
    user_heading: float, 
    target_lat: float, 
    target_lon: float, 
    cone_angle: float = 90
) -> bool:
    """
    Checks if a target location is within a forward-facing cone from the user.
    
    Args:
        user_lat, user_lon: User's current latitude and longitude.
        user_heading: User's current heading in degrees (0-360, 0 is North).
        target_lat, target_lon: Target location's latitude and longitude.
        cone_angle: The total angle of the cone (e.g., 90 for +/- 45 degrees from heading).
    
    Returns:
        True if the target is within the cone, False otherwise.
    """
    bearing_to_target = calculate_bearing(user_lat, user_lon, target_lat, target_lon)

    # Calculate the difference between user's heading and bearing to target
    angle_diff = abs(user_heading - bearing_to_target)

    # Normalize angle_diff to be within 0-180 degrees
    if angle_diff > 180:
        angle_diff = 360 - angle_diff

    return angle_diff <= (cone_angle / 2)

def get_time_context_label(hour: int) -> str:
    """
    Returns a time-of-day label based on the hour.
    """
    if 5 <= hour < 10:
        return "morning"
    elif 10 <= hour < 14:
        return "lunch"
    elif 14 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "dinner"
    else:
        return "night"

def get_time_context_query(hour: int) -> List[str]:
    """
    Returns a list of keywords for querying based on the time of day.
    """
    if 5 <= hour < 10:
        return ["coffee shop", "bakery", "breakfast", "cafe"]
    elif 10 <= hour < 14:
        return ["lunch", "restaurant", "cafe", "deli"]
    elif 14 <= hour < 18:
        return ["cafe", "snack", "park", "activity"]
    elif 18 <= hour < 22:
        return ["dinner", "restaurant", "bar"]
    else:
        return ["bar", "late night food", "activity"]

def _infer_types_from_name(name: str) -> List[str]:
    """
    Helper to infer place types from a place's name using keywords.
    Used for categorizing Lemon8 curated places.
    """
    inferred_types = []
    name_lower = name.lower()
    
    # Food-related
    if "restaurant" in name_lower or "eatery" in name_lower or "kitchen" in name_lower:
        inferred_types.append("restaurant")
    if "cafe" in name_lower or "coffee" in name_lower:
        inferred_types.append("cafe")
    if "bar" in name_lower or "pub" in name_lower:
        inferred_types.append("bar")
    if "pizza" in name_lower:
        inferred_types.append("pizza_restaurant")
    if "bakery" in name_lower:
        inferred_types.append("bakery")
    if "sushi" in name_lower or "japanese" in name_lower:
        inferred_types.append("japanese_restaurant")
    if "taco" in name_lower or "mexican" in name_lower:
        inferred_types.append("mexican_restaurant")
    if "thai" in name_lower:
        inferred_types.append("thai_restaurant")
    if "ice cream" in name_lower or "gelato" in name_lower:
        inferred_types.append("ice_cream_shop")
        
    # Activity/Place-related
    if "park" in name_lower:
        inferred_types.append("park")
    if "museum" in name_lower:
        inferred_types.append("museum")
    if "gallery" in name_lower or "art" in name_lower:
        inferred_types.append("art_gallery")
    if "shop" in name_lower or "store" in name_lower or "boutique" in name_lower:
        inferred_types.append("store")
    if "market" in name_lower:
        inferred_types.append("market")
        
    if not inferred_types:
        inferred_types.append("point_of_interest")
        
    return inferred_types

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
    # Approximately 0.002 degrees latitude/longitude \u2248 200m at NYC latitude
    lat_range = 0.002

def enrich_restaurant_data(place_data: Dict) -> Dict:
    """
    Placeholder for enriching restaurant data.
    """
    print(f"DEBUG: Enriching data for {place_data.get('name')}")
    return place_data

def filter_directional_places(
    user_lat: float, user_lon: float, user_heading: float, places: List[Dict], cone_angle: float = 90
) -> List[Dict]:
    """
    Placeholder for filtering places based on user's heading.
    """
    print(f"DEBUG: Filtering {len(places)} places directionally with heading {user_heading}")
    # For now, return all places. Implement actual filtering logic here later.
    return places
