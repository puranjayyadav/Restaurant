"""
Cost-efficient travel time matrix service with Haversine pre-filtering and OSRM routing.
Prevents API cost explosions by limiting matrix size to 25x25 (625 elements max).
"""
import requests
import math
import hashlib
import json
from typing import List, Dict, Tuple, Optional
from .utils import haversine_distance

# Optional import for Google Distance Matrix API
try:
    import googlemaps
    GOOGLEMAPS_AVAILABLE = True
except ImportError:
    GOOGLEMAPS_AVAILABLE = False


class RoutingService:
    """
    Travel time matrix service with cost protection.
    
    Strategy:
    1. Haversine pre-filter to top 25 candidates (free)
    2. OSRM for routing matrix (free, 95% accuracy)
    3. Google Distance Matrix as last resort (expensive, cached)
    4. Enhanced Haversine as final fallback
    """
    
    def __init__(self, osrm_url=None, google_api_key=None, cache=None):
        """
        Initialize routing service.
        
        Args:
            osrm_url: OSRM server URL (default: public demo server)
            google_api_key: Google Distance Matrix API key (optional)
            cache: Cache object with get/set methods (optional)
        """
        # Base URL for OSRM (without /route/v1 or /table/v1)
        self.osrm_url = osrm_url or "http://router.project-osrm.org"
        self.google_api_key = google_api_key
        self.cache = cache
        self.cache_ttl = 86400  # 24 hours
    
    def _haversine_pre_filter(self, places: List[Dict], start_location: Tuple[float, float], 
                             max_candidates: int = 25, max_distance_km: float = None) -> List[Dict]:
        """
        Pre-filter places using Haversine distance to reduce matrix size.
        
        Args:
            places: List of place dicts with lat/lng
            start_location: (lat, lng) of starting point
            max_candidates: Maximum number of candidates to keep
            max_distance_km: Optional maximum distance in km (filters by radius first)
        
        Returns:
            Filtered list of places within radius, then top N closest
        """
        if len(places) <= max_candidates and max_distance_km is None:
            return places
        
        start_lat, start_lng = start_location
        
        # Calculate distances
        places_with_distance = []
        for place in places:
            # Get coordinates
            if isinstance(place, dict):
                geometry = place.get('geometry', {})
                location = geometry.get('location', {})
                lat = location.get('lat')
                lng = location.get('lng')
            else:
                # ScrapedRestaurant object
                lat = float(place.latitude) if place.latitude else None
                lng = float(place.longitude) if place.longitude else None
            
            if lat and lng:
                distance_m = haversine_distance(start_lat, start_lng, lat, lng)
                distance_km = distance_m / 1000.0
                
                # If max_distance_km specified, filter by radius first
                if max_distance_km is None or distance_km <= max_distance_km:
                    places_with_distance.append((place, distance_m))
        
        # Sort by distance and take top N
        places_with_distance.sort(key=lambda x: x[1])
        filtered = [place for place, _ in places_with_distance[:max_candidates]]
        
        return filtered
    
    def _get_cache_key(self, places: List[Dict], mode: str) -> str:
        """Generate cache key for places and mode."""
        # Create hash from coordinates
        coords = []
        for place in places:
            if isinstance(place, dict):
                geometry = place.get('geometry', {})
                location = geometry.get('location', {})
                lat = location.get('lat')
                lng = location.get('lng')
            else:
                lat = float(place.latitude) if place.latitude else None
                lng = float(place.longitude) if place.longitude else None
            
            if lat and lng:
                coords.append(f"{lat:.6f},{lng:.6f}")
        
        coords_str = "|".join(sorted(coords))
        cache_key = f"routing_matrix_{mode}_{hashlib.md5(coords_str.encode()).hexdigest()}"
        return cache_key
    
    def _get_osrm_matrix(self, places: List[Dict], mode: str = 'walking') -> Optional[List[List[int]]]:
        """
        Get travel time matrix from OSRM.
        
        Args:
            places: List of place dicts with lat/lng
            mode: 'walking' or 'driving' (OSRM supports both)
        
        Returns:
            N×N matrix of travel times in minutes, or None if failed
        """
        try:
            # Build coordinates string for OSRM
            coords = []
            for place in places:
                if isinstance(place, dict):
                    geometry = place.get('geometry', {})
                    location = geometry.get('location', {})
                    lat = location.get('lat')
                    lng = location.get('lng')
                else:
                    lat = float(place.latitude) if place.latitude else None
                    lng = float(place.longitude) if place.longitude else None
                
                if lat and lng:
                    coords.append(f"{lng},{lat}")  # OSRM uses lng,lat format
            
            if not coords:
                return None
            
            coords_str = ";".join(coords)
            
            # OSRM table service endpoint format: /table/v1/{profile}/{coordinates}
            # Note: OSRM table service has a limit (usually 100 coordinates)
            # For the public demo server, we should stay under 25-30 coordinates
            profile = 'foot' if mode == 'walking' else 'driving'
            url = f"{self.osrm_url}/table/v1/{profile}/{coords_str}"
            
            # OSRM table service parameters
            # If sources/destinations not specified, computes all-to-all matrix
            # annotations=duration returns duration in response
            params = {
                'annotations': 'duration',
            }
            
            # For full matrix (all-to-all), we don't need to specify sources/destinations
            # OSRM will compute distances between all coordinates by default
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                durations = data.get('durations', [])
                
                if not durations:
                    print(f"OSRM API returned empty durations")
                    return None
                
                # Convert seconds to minutes
                matrix = []
                for row in durations:
                    matrix.append([int(d / 60) if d else 999999 for d in row])
                
                return matrix
            else:
                error_body = response.text[:200] if response.text else "No error details"
                print(f"OSRM API error: {response.status_code} - {error_body}")
                if response.status_code == 400:
                    print(f"DEBUG: OSRM URL: {url}")
                    print(f"DEBUG: OSRM params: {params}")
                    print(f"DEBUG: Number of coordinates: {len(coords)}")
                return None
                
        except Exception as e:
            print(f"OSRM request failed: {e}")
            return None
    
    def _get_google_matrix(self, places: List[Dict], mode: str = 'walking') -> Optional[List[List[int]]]:
        """
        Get travel time matrix from Google Distance Matrix API.
        EXPENSIVE: Only use as last resort.
        
        Args:
            places: List of place dicts with lat/lng
            mode: 'walking' or 'driving'
        
        Returns:
            N×N matrix of travel times in minutes, or None if failed
        """
        if not self.google_api_key:
            return None
        
        if not GOOGLEMAPS_AVAILABLE:
            return None
        
        try:
            gmaps = googlemaps.Client(key=self.google_api_key)
            
            # Extract coordinates
            origins = []
            destinations = []
            
            for place in places:
                if isinstance(place, dict):
                    geometry = place.get('geometry', {})
                    location = geometry.get('location', {})
                    lat = location.get('lat')
                    lng = location.get('lng')
                else:
                    lat = float(place.latitude) if place.latitude else None
                    lng = float(place.longitude) if place.longitude else None
                
                if lat and lng:
                    origins.append((lat, lng))
                    destinations.append((lat, lng))
            
            if not origins:
                return None
            
            # Google Distance Matrix API
            result = gmaps.distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=mode,
                units='metric'
            )
            
            # Parse response
            matrix = []
            for row in result['rows']:
                matrix_row = []
                for element in row['elements']:
                    if element['status'] == 'OK':
                        duration_seconds = element['duration']['value']
                        matrix_row.append(int(duration_seconds / 60))
                    else:
                        matrix_row.append(999999)  # Unreachable
                matrix.append(matrix_row)
            
            return matrix
            
        except Exception as e:
            print(f"Google Distance Matrix API error: {e}")
            return None
    
    def _get_haversine_matrix(self, places: List[Dict], mode: str = 'walking') -> List[List[int]]:
        """
        Generate travel time matrix using Haversine distance with realistic walk speeds.
        Final fallback if all routing services fail.
        
        Args:
            places: List of place dicts with lat/lng
            mode: 'walking' or 'driving'
        
        Returns:
            N×N matrix of travel times in minutes
        """
        # Walking speed: 5 km/h = 83.33 m/min
        # Route factor: 1.3x for city walking (not straight line)
        if mode == 'walking':
            speed_m_per_min = 83.33
            route_factor = 1.3
        else:
            # Driving: 30 km/h average in city = 500 m/min
            speed_m_per_min = 500
            route_factor = 1.2
        
        # Extract coordinates
        coords = []
        for place in places:
            if isinstance(place, dict):
                geometry = place.get('geometry', {})
                location = geometry.get('location', {})
                lat = location.get('lat')
                lng = location.get('lng')
            else:
                lat = float(place.latitude) if place.latitude else None
                lng = float(place.longitude) if place.longitude else None
            
            if lat and lng:
                coords.append((lat, lng))
            else:
                coords.append(None)
        
        # Build matrix
        matrix = []
        for i, coord1 in enumerate(coords):
            row = []
            for j, coord2 in enumerate(coords):
                if coord1 and coord2:
                    distance_m = haversine_distance(coord1[0], coord1[1], coord2[0], coord2[1])
                    # Apply route factor and convert to minutes
                    time_minutes = int((distance_m * route_factor) / speed_m_per_min)
                    row.append(max(1, time_minutes))  # Minimum 1 minute
                else:
                    row.append(999999)  # Unreachable
            matrix.append(row)
        
        return matrix
    
    def get_travel_time_matrix(self, places: List[Dict], start_location: Tuple[float, float],
                               mode: str = 'walking', max_candidates: int = 25, 
                               max_distance_km: float = None) -> Tuple[List[List[int]], List[int]]:
        """
        Get travel time matrix with cost protection.
        
        Args:
            places: List of place dicts with lat/lng
            start_location: (lat, lng) of starting point
            mode: 'walking' or 'driving'
            max_candidates: Maximum candidates after Haversine pre-filter (default: 25)
            max_distance_km: Optional maximum distance in km for radius filtering
        
        Returns:
            Tuple of (N×N time matrix in minutes, list of original indices)
        """
        # Step 1: Haversine pre-filter (CRITICAL: Prevents cost explosion)
        # If max_distance_km provided, filter by radius first, then take top N
        filtered_places = self._haversine_pre_filter(places, start_location, max_candidates, max_distance_km)
        
        # Build index mapping (filtered index -> original index)
        original_indices = []
        for place in filtered_places:
            # Find original index
            for i, orig_place in enumerate(places):
                if place is orig_place:
                    original_indices.append(i)
                    break
        
        # Add start location as first place in matrix
        places_with_start = [{'geometry': {'location': {'lat': start_location[0], 'lng': start_location[1]}}}] + filtered_places
        original_indices = [-1] + original_indices  # -1 indicates start location
        
        # Check cache
        cache_key = self._get_cache_key(places_with_start, mode)
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached, original_indices
        
        # Step 2: Try OSRM (free, primary)
        matrix = self._get_osrm_matrix(places_with_start, mode)
        
        # Step 3: Try Google (expensive, only if OSRM fails)
        if matrix is None and self.google_api_key:
            matrix = self._get_google_matrix(places_with_start, mode)
        
        # Step 4: Fallback to Haversine (always works)
        if matrix is None:
            matrix = self._get_haversine_matrix(places_with_start, mode)
        
        # Cache result
        if self.cache and matrix:
            self.cache.set(cache_key, matrix, self.cache_ttl)
        
        return matrix, original_indices

