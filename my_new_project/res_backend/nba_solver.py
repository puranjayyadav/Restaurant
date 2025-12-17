"""
Next Best Action (NBA) Solver for real-time recommendations.
Implements rolling horizon approach - returns only the next 2 steps instead of full itinerary.
"""

import os
import django
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
import math

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

from .utils import (
    haversine_distance,
    calculate_bearing,
    is_in_forward_cone,
    get_time_context_label,
    get_time_context_query
)


class NBASolver:
    """
    Solves for the next best action using simplified scoring.
    Returns only the next stop and a backup option.
    """
    
    def solve_next_action(
        self,
        user_location: Tuple[float, float],
        heading: Optional[float],
        current_time: datetime,
        places: List[Dict],
        user_preferences: Optional[Dict] = None
    ) -> Dict:
        """
        Solve for next best action.
        
        Args:
            user_location: (lat, lon) tuple
            heading: User's heading in degrees (None if unknown)
            current_time: Current datetime
            places: List of place dictionaries
            user_preferences: Optional dict with user preferences
        
        Returns:
            Dict with next_stop, backup_stop, context, confidence
        """
        if not places:
            return {
                "next_stop": None,
                "backup_stop": None,
                "context": get_time_context_label(current_time.hour),
                "confidence": 0.0
            }
        
        user_lat, user_lon = user_location
        current_hour = current_time.hour
        
        # Filter places that are open now
        open_places = self._filter_open_now(places, current_time)
        if not open_places:
            # If no places are open, use all places (fallback)
            open_places = places
        
        # Apply directional filter if heading available
        if heading is not None:
            filtered_places = []
            for place in open_places:
                place_lat, place_lon = self._extract_coordinates(place)
                if place_lat is None:
                    continue
                
                if is_in_forward_cone(user_lat, user_lon, heading, place_lat, place_lon, cone_angle=120):
                    filtered_places.append(place)
            
            if filtered_places:
                open_places = filtered_places
        
        # Score all places
        scored_places = []
        for place in open_places:
            score = self._calculate_simple_score(
                place, user_location, heading, current_time, user_preferences
            )
            scored_places.append((place, score))
        
        # Sort by score (highest first)
        scored_places.sort(key=lambda x: x[1], reverse=True)
        
        # Get next stop (best option)
        next_stop = None
        if scored_places:
            next_place, next_score = scored_places[0]
            next_stop = self._format_stop(next_place, user_location, current_time)
        
        # Get backup stop (second best, or best if no next_stop)
        backup_stop = None
        if len(scored_places) > 1:
            backup_place, backup_score = scored_places[1]
            backup_stop = self._format_stop(backup_place, user_location, current_time)
        elif len(scored_places) == 1 and next_stop:
            # Use next_stop as backup if only one option
            backup_stop = next_stop
        
        # Calculate confidence based on score difference
        confidence = 0.5  # Default
        if len(scored_places) >= 2:
            best_score = scored_places[0][1]
            second_score = scored_places[1][1]
            if best_score > 0:
                confidence = min(0.95, 0.5 + (best_score - second_score) / best_score * 0.45)
        elif len(scored_places) == 1:
            best_score = scored_places[0][1]
            confidence = min(0.9, 0.5 + best_score / 100.0 * 0.4)
        
        return {
            "next_stop": next_stop,
            "backup_stop": backup_stop,
            "context": get_time_context_label(current_hour),
            "confidence": round(confidence, 2)
        }
    
    def _calculate_simple_score(
        self,
        place: Dict,
        user_location: Tuple[float, float],
        heading: Optional[float],
        current_time: datetime,
        user_preferences: Optional[Dict] = None
    ) -> float:
        """
        Calculate simple score for a place.
        
        Scoring formula:
        score = (rating * 0.4) + (distance_score * 0.3) + (time_match * 0.2) + (open_now * 0.1)
        
        Args:
            place: Place dictionary
            user_location: (lat, lon) tuple
            heading: User's heading in degrees
            current_time: Current datetime
            user_preferences: Optional user preferences
        
        Returns:
            Score (0-100)
        """
        user_lat, user_lon = user_location
        
        # Extract coordinates
        place_lat, place_lon = self._extract_coordinates(place)
        if place_lat is None:
            return 0.0
        
        # 1. Rating score (0-40 points)
        rating = place.get('rating') or place.get('avg_rating') or 0.0
        rating_score = (float(rating) / 5.0) * 40.0
        
        # 2. Distance score (0-30 points)
        distance_m = haversine_distance(user_lat, user_lon, place_lat, place_lon)
        distance_km = distance_m / 1000.0
        
        # Prefer places within 500m, penalize beyond 1km
        if distance_km <= 0.5:
            distance_score = 30.0
        elif distance_km <= 1.0:
            distance_score = 30.0 * (1.0 - (distance_km - 0.5) / 0.5)
        else:
            # Heavy penalty for far places
            distance_score = max(0.0, 15.0 * (1.0 - (distance_km - 1.0) / 2.0))
        
        # Bonus for forward direction if heading available
        if heading is not None:
            bearing_to_place = calculate_bearing(user_lat, user_lon, place_lat, place_lon)
            angle_diff = abs(bearing_to_place - heading)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            # Bonus if within 30° of heading
            if angle_diff <= 30:
                distance_score *= 1.2  # 20% bonus
            elif angle_diff <= 60:
                distance_score *= 1.1  # 10% bonus
        
        distance_score = min(30.0, distance_score)
        
        # 3. Time match score (0-20 points)
        current_hour = current_time.hour
        time_context_keywords = get_time_context_query(current_hour)
        
        place_types = []
        if 'types' in place:
            place_types = [t.lower() for t in place.get('types', [])]
        elif 'categories' in place:
            place_types = [c.lower() for c in place.get('categories', [])]
        
        time_match_score = 0.0
        for keyword in time_context_keywords:
            keyword_lower = keyword.lower()
            if any(keyword_lower in pt for pt in place_types):
                time_match_score += 20.0 / len(time_context_keywords)
        
        time_match_score = min(20.0, time_match_score)
        
        # 4. Open now score (0-10 points)
        open_now_score = 10.0 if self._is_open_now(place, current_time) else 0.0
        
        # Total score
        total_score = rating_score + distance_score + time_match_score + open_now_score
        
        # User preference bonus (optional, up to +10 points)
        if user_preferences:
            # Check cuisine match
            if user_preferences.get('preferred_cuisines'):
                preferred = [c.lower() for c in user_preferences['preferred_cuisines']]
                place_name = (place.get('name') or '').lower()
                if any(cuisine in place_name for cuisine in preferred):
                    total_score += 10.0
        
        return min(100.0, total_score)
    
    def _filter_open_now(self, places: List[Dict], current_time: datetime) -> List[Dict]:
        """
        Filter places that are likely open now.
        
        Args:
            places: List of place dictionaries
            current_time: Current datetime
        
        Returns:
            Filtered list of places that are open
        """
        current_hour = current_time.hour
        current_weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        open_places = []
        
        for place in places:
            hours = place.get('hours') or place.get('opening_hours') or []
            
            if not hours:
                # If no hours data, assume open (can't verify)
                open_places.append(place)
                continue
            
            # Check if place is open
            if self._is_open_now(place, current_time):
                open_places.append(place)
        
        return open_places
    
    def _is_open_now(self, place: Dict, current_time: datetime) -> bool:
        """
        Check if place is open now based on hours data.
        
        Args:
            place: Place dictionary
            current_time: Current datetime
        
        Returns:
            True if likely open, False otherwise
        """
        hours = place.get('hours') or place.get('opening_hours') or []
        
        if not hours:
            # No hours data - assume open
            return True
        
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_time_minutes = current_hour * 60 + current_minute
        
        # Try to parse hours (format varies)
        # Common formats:
        # - List of dicts: [{"day": 0, "hours": "9:00 AM - 10:00 PM"}, ...]
        # - Dict: {"monday": "9:00 AM - 10:00 PM", ...}
        
        current_weekday = current_time.weekday()  # 0 = Monday
        
        for hour_entry in hours:
            if isinstance(hour_entry, dict):
                day = hour_entry.get('day')
                if day == current_weekday:
                    hours_str = hour_entry.get('hours') or hour_entry.get('hours_str')
                    if hours_str:
                        # Try to parse "9:00 AM - 10:00 PM"
                        if self._parse_hours_string(hours_str, current_time_minutes):
                            return True
        
        # If can't determine, assume open (conservative)
        return True
    
    def _parse_hours_string(self, hours_str: str, current_time_minutes: int) -> bool:
        """
        Parse hours string like "9:00 AM - 10:00 PM" and check if current time is within range.
        
        Args:
            hours_str: Hours string
            current_time_minutes: Current time in minutes from midnight
        
        Returns:
            True if current time is within range
        """
        try:
            # Simple parsing - look for time patterns
            import re
            pattern = r'(\d{1,2}):(\d{2})\s*(AM|PM)'
            matches = re.findall(pattern, hours_str.upper())
            
            if len(matches) >= 2:
                open_hour, open_min, open_ampm = matches[0]
                close_hour, close_min, close_ampm = matches[1]
                
                open_hour = int(open_hour)
                open_min = int(open_min)
                close_hour = int(close_hour)
                close_min = int(close_min)
                
                # Convert to 24-hour format
                if open_ampm == 'PM' and open_hour != 12:
                    open_hour += 12
                if open_ampm == 'AM' and open_hour == 12:
                    open_hour = 0
                
                if close_ampm == 'PM' and close_hour != 12:
                    close_hour += 12
                if close_ampm == 'AM' and close_hour == 12:
                    close_hour = 0
                
                open_minutes = open_hour * 60 + open_min
                close_minutes = close_hour * 60 + close_min
                
                # Handle overnight hours (e.g., 10 PM - 2 AM)
                if close_minutes < open_minutes:
                    close_minutes += 24 * 60
                    if current_time_minutes < open_minutes:
                        current_time_minutes += 24 * 60
                
                return open_minutes <= current_time_minutes <= close_minutes
        except Exception:
            pass
        
        # If parsing fails, assume open
        return True
    
    def _extract_coordinates(self, place: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Extract lat/lon from place dict."""
        if 'lat' in place and 'lng' in place:
            return float(place['lat']), float(place['lng'])
        elif 'lat' in place and 'long' in place:
            return float(place['lat']), float(place['long'])
        elif 'geometry' in place and 'location' in place['geometry']:
            loc = place['geometry']['location']
            return float(loc.get('lat', 0)), float(loc.get('lng', loc.get('long', 0)))
        return None, None
    
    def _format_stop(
        self,
        place: Dict,
        user_location: Tuple[float, float],
        current_time: datetime
    ) -> Dict:
        """
        Format place as stop with distance, bearing, estimated arrival.
        
        Args:
            place: Place dictionary
            user_location: (lat, lon) tuple
            current_time: Current datetime
        
        Returns:
            Formatted stop dict
        """
        user_lat, user_lon = user_location
        place_lat, place_lon = self._extract_coordinates(place)
        
        if place_lat is None:
            return None
        
        # Calculate distance
        distance_m = haversine_distance(user_lat, user_lon, place_lat, place_lon)
        
        # Calculate bearing
        bearing = calculate_bearing(user_lat, user_lon, place_lat, place_lon)
        bearing_cardinal = self._bearing_to_cardinal(bearing)
        
        # Estimate arrival time (walking speed ~5 km/h = 1.39 m/s)
        walking_speed_ms = 1.39
        estimated_seconds = distance_m / walking_speed_ms
        estimated_arrival = current_time + timedelta(seconds=estimated_seconds)
        
        # Format arrival time (Windows-compatible format)
        hour_12 = estimated_arrival.hour % 12
        if hour_12 == 0:
            hour_12 = 12
        am_pm = "AM" if estimated_arrival.hour < 12 else "PM"
        arrival_str = f"{hour_12}:{estimated_arrival.minute:02d} {am_pm}"
        
        return {
            "name": place.get('name') or 'Unknown',
            "place_id": place.get('place_id') or '',
            "distance_m": int(distance_m),
            "distance_km": round(distance_m / 1000.0, 2),
            "bearing": bearing_cardinal,
            "bearing_degrees": round(bearing, 1),
            "estimated_arrival": arrival_str,
            "rating": place.get('rating') or place.get('avg_rating'),
            "types": place.get('types') or place.get('categories') or [],
            "address": place.get('formatted_address') or place.get('address') or place.get('full_address') or '',
            # Keep raw coordinates so rolling simulations can re-anchor
            "lat": place_lat,
            "lng": place_lon,
        }
    
    def _bearing_to_cardinal(self, bearing: float) -> str:
        """Convert bearing in degrees to cardinal direction."""
        cardinals = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = int((bearing + 22.5) / 45.0) % 8
        return cardinals[index]


class DynamicItinerarySolver(NBASolver):
    """
    Rolling-chain itinerary solver.
    Simulates future steps by advancing time/location after each recommended stop.
    """

    DWELL_TIMES = {
        'coffee': 30,
        'cafe': 45,
        'bakery': 20,
        'park': 45,
        'museum': 90,
        'shopping': 60,
        'lunch': 60,
        'dinner': 90,
        'bar': 60,
        'general': 60,
    }

    def generate_rolling_itinerary(
        self,
        user_location: Tuple[float, float],
        heading: Optional[float],
        current_time: datetime,
        places: List[Dict],
        steps: int = 4
    ) -> List[Dict]:
        """
        Generate a multi-step chain (A -> B -> C) using simulated future states.
        """
        itinerary: List[Dict] = []
        sim_location = user_location
        sim_heading = heading
        sim_time = current_time
        used_place_ids: Set[str] = set()

        for i in range(max(1, steps)):
            # Filter out already visited
            available_places = [
                p for p in places
                if (p.get('place_id') or p.get('name')) not in used_place_ids
            ]
            if not available_places:
                break

            step_result = self.solve_next_action(
                user_location=sim_location,
                heading=sim_heading,
                current_time=sim_time,
                places=available_places,
                user_preferences=None
            )
            best_stop = step_result.get('next_stop')
            if not best_stop:
                break

            # Enrich with chain metadata
            best_stop = best_stop.copy()
            best_stop['step_sequence'] = i + 1
            best_stop['visit_context'] = get_time_context_label(sim_time.hour)
            best_stop['simulated_arrival'] = best_stop.get('estimated_arrival')
            itinerary.append(best_stop)

            # Update simulation state
            place_lat, place_lon = self._extract_coordinates(best_stop)
            if place_lat is None:
                break

            distance_m = best_stop.get('distance_m') or 0
            travel_minutes = self._estimate_travel_minutes(distance_m)
            dwell_minutes = self.DWELL_TIMES.get(self._infer_category(best_stop), 60)
            sim_time = sim_time + timedelta(minutes=travel_minutes + dwell_minutes)
            sim_location = (place_lat, place_lon)
            sim_heading = None  # allow 360° after first hop

            place_id = best_stop.get('place_id') or best_stop.get('name')
            if place_id:
                used_place_ids.add(place_id)

        return itinerary

    def _estimate_travel_minutes(self, distance_m: float) -> int:
        """Estimate walking travel minutes given distance (meters)."""
        walking_speed_ms = 1.39  # ~5 km/h
        seconds = distance_m / walking_speed_ms if distance_m else 0
        return max(5, int(round(seconds / 60.0)))

    def _infer_category(self, stop: Dict) -> str:
        """Infer a coarse category from types for dwell-time lookup."""
        types = stop.get('types') or []
        for t in types:
            lower_t = str(t).lower()
            for key in self.DWELL_TIMES.keys():
                if key in lower_t:
                    return key
        return 'general'

