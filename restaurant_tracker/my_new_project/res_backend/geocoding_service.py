"""
Geocoding service with non-deterministic randomization for location hints.
Uses OpenStreetMap (Photon API) for geocoding.
Restricted to NYC bounds only.
"""
import requests
import urllib.parse
import random
import math
from typing import Tuple, Optional

# NYC bounds for filtering geocoded results
NYC_BOUNDS = {
    'min_lat': 40.4774,  # Southernmost point (Staten Island)
    'max_lat': 40.9176,  # Northernmost point (Bronx)
    'min_lon': -74.2591,  # Westernmost point (New Jersey border)
    'max_lon': -73.7004,  # Easternmost point (Queens)
}
NYC_CENTER = (40.7128, -74.0060)  # Manhattan center (fallback)


def is_within_nyc_bounds(lat: float, lon: float) -> bool:
    """Check if coordinates are within NYC bounds"""
    return (
        NYC_BOUNDS['min_lat'] <= lat <= NYC_BOUNDS['max_lat'] and
        NYC_BOUNDS['min_lon'] <= lon <= NYC_BOUNDS['max_lon']
    )


def geocode_with_randomization(location_hint: str, random_seed: Optional[str] = None) -> Tuple[float, float]:
    """
    Geocode a location hint (e.g., "DUMBO", "midtown") to coordinates with non-deterministic randomization.
    
    The same location geocodes to the same base coordinates, but adds a truly random offset
    within a reasonable radius (500m-2km) for variety. Each call generates different coordinates,
    so "midtown" will explore different parts of midtown each time.
    
    Args:
        location_hint: Location name (neighborhood, city, etc.)
        random_seed: Optional seed for randomization (ignored - uses true randomization)
    
    Returns:
        Tuple of (latitude, longitude) with randomized offset
    """
    if not location_hint or not location_hint.strip():
        return NYC_CENTER[0], NYC_CENTER[1]  # NYC center fallback
    
    location_hint = location_hint.strip()
    
    # NO SEEDING - use true randomization for variety
    # This ensures each call gets different coordinates within the location
    
    try:
        # #region agent log
        import json
        import os
        log_path = r'c:\Users\PURANJAY\OneDrive\Documents\Res_2\.cursor\debug.log'
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'sessionId': 'debug-session',
                    'runId': 'run1',
                    'hypothesisId': 'A',
                    'location': 'geocoding_service.py:50',
                    'message': 'Starting geocoding (NYC-only)',
                    'data': {'location_hint': location_hint, 'randomization': 'non-deterministic'},
                    'timestamp': int(__import__('time').time() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        # Try multiple query variations to find NYC results
        query_variations = [
            location_hint,  # Original query
            f"{location_hint}, New York",  # Add "New York"
            f"{location_hint}, NYC",  # Add "NYC"
            f"{location_hint}, New York City",  # Add "New York City"
        ]
        
        for query_variant in query_variations:
            # Geocode using Photon API (OpenStreetMap)
            encoded_name = urllib.parse.quote(query_variant)
            url = f"https://photon.komoot.io/api/?q={encoded_name}&limit=5"  # Get more results to filter
            headers = {'User-Agent': 'ResBackend/1.0 (contact@example.com)'}
            
            response = requests.get(url, timeout=5, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('features'):
                    # Find first feature within NYC bounds
                    for feature in data['features']:
                        coords = feature['geometry']['coordinates']
                        # Photon returns [lon, lat], we need (lat, lon)
                        base_lat = float(coords[1])
                        base_lon = float(coords[0])
                        
                        # #region agent log
                        try:
                            with open(log_path, 'a', encoding='utf-8') as f:
                                f.write(json.dumps({
                                    'sessionId': 'debug-session',
                                    'runId': 'run1',
                                    'hypothesisId': 'A',
                                    'location': 'geocoding_service.py:75',
                                    'message': 'Checking coordinates against NYC bounds',
                                    'data': {
                                        'base_lat': base_lat,
                                        'base_lon': base_lon,
                                        'query_variant': query_variant,
                                        'within_nyc': is_within_nyc_bounds(base_lat, base_lon)
                                    },
                                    'timestamp': int(__import__('time').time() * 1000)
                                }) + '\n')
                        except: pass
                        # #endregion
                        
                        # Only proceed if coordinates are within NYC bounds
                        if not is_within_nyc_bounds(base_lat, base_lon):
                            continue  # Try next feature
                        
                        # #region agent log
                        try:
                            with open(log_path, 'a', encoding='utf-8') as f:
                                f.write(json.dumps({
                                    'sessionId': 'debug-session',
                                    'runId': 'run1',
                                    'hypothesisId': 'A',
                                    'location': 'geocoding_service.py:95',
                                    'message': 'Found NYC coordinates, applying randomization',
                                    'data': {'base_lat': base_lat, 'base_lon': base_lon},
                                    'timestamp': int(__import__('time').time() * 1000)
                                }) + '\n')
                        except: pass
                        # #endregion
                        
                        # Add truly random offset (500m - 2km radius) for variety
                        # Each call generates different coordinates within the location
                        # Larger radius for bigger areas like "midtown" to explore more variety
                        offset_distance_m = random.uniform(500, 2000)  # 500m to 2km for more variety
                        offset_bearing_deg = random.uniform(0, 360)  # Random direction in degrees
                        offset_bearing_rad = math.radians(offset_bearing_deg)
                        
                        # Convert offset to lat/lon delta using bearing
                        # 1 degree latitude ≈ 111km, 1 degree longitude ≈ 111km * cos(latitude)
                        lat_offset_km = (offset_distance_m / 1000) * math.cos(offset_bearing_rad)
                        lon_offset_km = (offset_distance_m / 1000) * math.sin(offset_bearing_rad) / math.cos(math.radians(base_lat))
                        
                        # Convert km to degrees
                        lat_offset = lat_offset_km / 111.0
                        lon_offset = lon_offset_km / 111.0
                        
                        # Apply offset
                        randomized_lat = base_lat + lat_offset
                        randomized_lon = base_lon + lon_offset
                        
                        # Ensure randomized coordinates are still within NYC bounds
                        # If offset pushes outside bounds, clamp to bounds
                        randomized_lat = max(NYC_BOUNDS['min_lat'], min(NYC_BOUNDS['max_lat'], randomized_lat))
                        randomized_lon = max(NYC_BOUNDS['min_lon'], min(NYC_BOUNDS['max_lon'], randomized_lon))
                        
                        # #region agent log
                        try:
                            with open(log_path, 'a', encoding='utf-8') as f:
                                f.write(json.dumps({
                                    'sessionId': 'debug-session',
                                    'runId': 'run1',
                                    'hypothesisId': 'A',
                                    'location': 'geocoding_service.py:125',
                                    'message': 'Randomized coordinates (NYC-bounded)',
                                    'data': {
                                        'randomized_lat': randomized_lat,
                                        'randomized_lon': randomized_lon,
                                        'base_lat': base_lat,
                                        'base_lon': base_lon,
                                        'offset_distance_m': offset_distance_m,
                                        'offset_bearing_deg': offset_bearing_deg,
                                        'within_nyc': is_within_nyc_bounds(randomized_lat, randomized_lon)
                                    },
                                    'timestamp': int(__import__('time').time() * 1000)
                                }) + '\n')
                        except: pass
                        # #endregion
                        
                        return randomized_lat, randomized_lon
                    
                    # If we got here, no features were within NYC bounds
                    print(f"WARNING: Photon returned results for '{query_variant}' but none within NYC bounds")
                    continue  # Try next query variation
                else:
                    # No features for this query variant, try next
                    continue
            else:
                print(f"WARNING: Photon API returned status {response.status_code} for '{query_variant}'")
                continue  # Try next query variation
    except Exception as e:
        print(f"ERROR: Geocoding failed for '{location_hint}': {e}")
    
    # Fallback to NYC center if all queries failed or returned non-NYC results
    print(f"WARNING: Using NYC fallback coordinates for '{location_hint}' (no NYC results found)")
    return NYC_CENTER[0], NYC_CENTER[1]

