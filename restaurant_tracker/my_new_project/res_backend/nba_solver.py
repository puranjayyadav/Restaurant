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
    Also supports full-day itinerary generation via recursive chaining.
    """
    
    # Dwell time estimates in minutes by category
    DWELL_TIMES = {
        'cafe': 45,
        'coffee': 30,
        'bakery': 20,
        'breakfast': 45,
        'restaurant': 90,
        'dinner': 120,
        'lunch': 60,
        'bar': 75,
        'lounge': 90,
        'nightlife': 120,
        'museum': 90,
        'park': 45,
        'shopping': 60,
        'gallery': 60,
        'landmark': 30,
        'theater': 150,
        'spot': 60,  # Default
    }
    
    def generate_full_day_itinerary(
        self,
        user_location: Tuple[float, float],
        start_time: datetime,
        places: List[Dict],
        max_steps: int = 5,
        max_distance_km: float = 5.0,
        user_preferences: Optional[Dict] = None
    ) -> Dict:
        """
        Generate a full-day itinerary using recursive chaining.
        
        Args:
            user_location: Starting (lat, lon) tuple
            start_time: Starting datetime
            places: List of all available places
            max_steps: Maximum number of stops (default 5)
            max_distance_km: Maximum total walking distance in km (default 5.0)
        
        Returns:
            Dict with full itinerary, total_distance, total_duration, narrative_arc
        """
        full_itinerary = []
        current_loc = user_location
        current_time = start_time
        visited_ids = set()
        total_distance_m = 0
        last_category = None  # Track previous category for hard filter
        
        for step_idx in range(max_steps):
            # 1. HARD FILTER: Remove visited places AND immediate category duplicates
            available = []
            for p in places:
                # Always exclude visited
                if p.get('place_id') in visited_ids:
                    continue
                
                # Check category duplicate (only if we have a last category)
                current_cat = p.get('solver_data', {}).get('category_normalized', '').lower()
                if last_category and current_cat and current_cat == last_category:
                    continue
                
                available.append(p)
            
            # Fallback: If filter removed everything (e.g. coffee district), allow duplicates
            # but the _apply_category_bias will still penalize them
            if not available:
                available = [p for p in places if p.get('place_id') not in visited_ids]
                if not available:
                    break
            
            # 2. Apply category bias based on current time for narrative arc
            prioritized = self._apply_category_bias(available, current_time, step_idx, full_itinerary)
            
            # 3. Solve for single best next action
            result = self.solve_next_action(
                user_location=current_loc,
                heading=None,  # Heading only matters for initial step
                current_time=current_time,
                places=prioritized,
                user_preferences=user_preferences
            )
            
            itinerary_segment = result.get('itinerary', [])
            if not itinerary_segment:
                break
            
            next_stop = itinerary_segment[0]  # Take only the first step
            if not next_stop:
                break
            
            # 4. Check total distance constraint (max exhaustion)
            step_distance_m = next_stop.get('distance_m', 0)
            if total_distance_m + step_distance_m > max_distance_km * 1000:
                break  # Would exceed max walking distance
            
            # 5. Update state
            next_stop['step'] = step_idx + 1
            full_itinerary.append(next_stop)
            visited_ids.add(next_stop.get('place_id'))
            total_distance_m += step_distance_m
            
            # Update last category for next iteration's filter
            last_category = next_stop.get('category_normalized', '').lower()
            
            # 6. Advance time & location
            travel_minutes = self._estimate_travel_minutes(step_distance_m)
            
            # Use enriched duration_minutes from Lemon8 if available
            dwell_minutes = next_stop.get('duration_minutes')
            if not dwell_minutes:
                # Fallback to category-based estimate
                category = next_stop.get('category_normalized', '').lower()
                dwell_minutes = self.DWELL_TIMES.get(category, 60)
            
            current_time += timedelta(minutes=travel_minutes + dwell_minutes)
            current_loc = (next_stop['lat'], next_stop['lng'])
            
            # 7. Stop if we've reached end of day (after 10 PM)
            if current_time.hour >= 22:
                break
        
        # Generate narrative arc description
        narrative_arc = self._generate_narrative_arc(full_itinerary, start_time)
        
        return {
            "itinerary": full_itinerary,
            "total_steps": len(full_itinerary),
            "total_distance_m": int(total_distance_m),
            "total_distance_km": round(total_distance_m / 1000, 2),
            "start_time": start_time.isoformat(),
            "end_time": current_time.isoformat(),
            "narrative_arc": narrative_arc
        }
    
    def _estimate_travel_minutes(self, distance_m: float) -> int:
        """Estimate travel time in minutes. Walking speed ~5 km/h = 83.3 m/min."""
        return int(distance_m / 83.3)
    
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
                "context": get_time_context_label(current_time.hour),
                "confidence": 0.0,
                "summary": "No places available in this area.",
                "itinerary": [],
                "backup_option": None
            }
        
        user_lat, user_lon = user_location
        current_hour = current_time.hour
        
        # Filter places that are open now
        open_places = self._filter_open_now(places, current_time)
        if not open_places:
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
        
        # === STEP 1: Find the "Anchor" (Best primary stop) ===
        scored_places = []
        for place in open_places:
            score = self._calculate_simple_score(
                place, user_location, heading, current_time, user_preferences
            )
            place_lat, place_lon = self._extract_coordinates(place)
            distance_m = haversine_distance(user_lat, user_lon, place_lat, place_lon) if place_lat else 9999
            vibe_bonus = self._calculate_vibe_bonus(place, current_time)
            scored_places.append((place, score, distance_m, vibe_bonus))
        
        scored_places.sort(key=lambda x: x[1], reverse=True)
        
        if not scored_places:
            return {
                "context": get_time_context_label(current_hour),
                "confidence": 0.0,
                "summary": "No matching places found.",
                "itinerary": [],
                "backup_option": None
            }
        
        # Step 1 - The Anchor
        step1_place, step1_score, step1_dist, step1_vibe_bonus = scored_places[0]
        step1_lat, step1_lon = self._extract_coordinates(step1_place)
        step1_rating = step1_place.get('rating') or step1_place.get('avg_rating') or 0
        
        step1_formatted = self._format_stop(step1_place, user_location, current_time)
        step1_formatted['step'] = 1
        step1_formatted['vibe'] = self._infer_primary_vibe(step1_place)
        step1_formatted['reason'] = self._generate_reason(
            step1_place, step1_dist, step1_vibe_bonus, step1_rating, current_time
        )
        step1_formatted['coords'] = [step1_lat, step1_lon]
        
        # === STEP 2: The Rolling Chain ===
        # Score remaining places from Step 1's coordinates with Vee constraint
        # AND category diversity (prevent duplicate categories)
        step1_solver_data = step1_place.get('solver_data') or {}
        step1_category = step1_solver_data.get('category_normalized', '').lower()
        
        step2_candidates = []
        for place, orig_score, orig_dist, vibe_bonus in scored_places[1:]:
            place_lat, place_lon = self._extract_coordinates(place)
            if place_lat is None:
                continue
            
            # Category diversity: Skip if same category as Step 1
            place_solver_data = place.get('solver_data') or {}
            place_category = place_solver_data.get('category_normalized', '').lower()
            if step1_category and place_category and step1_category == place_category:
                continue  # Skip duplicate categories for experience diversity
            
            # Distance from Step 1
            dist_from_step1 = haversine_distance(step1_lat, step1_lon, place_lat, place_lon)
            
            # Vee constraint: Total displacement from user <= 1.5km
            dist_from_user = haversine_distance(user_lat, user_lon, place_lat, place_lon)
            total_displacement = step1_dist + dist_from_step1
            
            # Only consider places within 300m of Step 1 AND total displacement <= 1.5km
            if dist_from_step1 <= 300 and total_displacement <= 1500:
                # Re-score with Step 1 as anchor
                adjusted_score = orig_score * (1 - dist_from_step1 / 500)  # Prefer closer
                step2_candidates.append((place, adjusted_score, dist_from_step1, vibe_bonus))
        
        step2_candidates.sort(key=lambda x: x[1], reverse=True)
        
        step2_formatted = None
        if step2_candidates:
            step2_place, step2_score, step2_dist, step2_vibe_bonus = step2_candidates[0]
            step2_lat, step2_lon = self._extract_coordinates(step2_place)
            step2_rating = step2_place.get('rating') or step2_place.get('avg_rating') or 0
            
            # Estimate arrival at Step 2 (after dwell at Step 1)
            step1_arrival = current_time + timedelta(seconds=step1_dist / 1.39)
            step1_dwell = timedelta(minutes=45)  # Default dwell
            step2_arrival = step1_arrival + step1_dwell + timedelta(seconds=step2_dist / 1.39)
            
            step2_formatted = self._format_stop(step2_place, (step1_lat, step1_lon), step2_arrival)
            step2_formatted['step'] = 2
            step2_formatted['vibe'] = self._infer_primary_vibe(step2_place)
            step2_formatted['reason'] = self._generate_reason(
                step2_place, step2_dist, step2_vibe_bonus, step2_rating, current_time
            )
            step2_formatted['coords'] = [step2_lat, step2_lon]
        
        # === BACKUP OPTION ===
        # Use the robust backup selector that matches category and vibe
        backup_option = self._select_backup_option(step1_formatted, scored_places)
        
        # Fallback if no category-matched backup found
        if not backup_option and len(scored_places) > 1:
            alt_place = scored_places[1][0]
            backup_option = {
                "name": alt_place.get('name') or 'Unknown',
                "reason": "The second-best rated option in the area."
            }
        
        # === CONFIDENCE ===
        confidence = 0.5
        if len(scored_places) >= 2:
            best_score = scored_places[0][1]
            second_score = scored_places[1][1]
            if best_score > 0:
                confidence = min(0.95, 0.5 + (best_score - second_score) / best_score * 0.45)
        elif len(scored_places) == 1:
            confidence = min(0.9, 0.5 + scored_places[0][1] / 100.0 * 0.4)
        
        # === BUILD RESPONSE ===
        itinerary = [step1_formatted]
        if step2_formatted:
            itinerary.append(step2_formatted)
        
        return {
            "context": get_time_context_label(current_hour),
            "confidence": round(confidence, 2),
            "summary": self._generate_summary(step1_formatted, step2_formatted),
            "itinerary": itinerary,
            "backup_option": backup_option
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
        try:
            rating_score = (float(rating) / 5.0) * 40.0
        except (ValueError, TypeError):
            rating_score = 0.0
        
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
        
        # 5. Time Bias Boost (0-30 points) from Lemon8 enriched data
        time_bias_score = self._calculate_time_bias_score(place, current_time)
        total_score += time_bias_score
        
        # 6. Vibe bonus (0-20 points) for time-aware atmosphere matching
        vibe_bonus = self._calculate_vibe_bonus(place, current_time)
        total_score += vibe_bonus
        
        # 7. Dynamic Boost (0-80 points) from recursive chain narrative logic
        # Injected by _apply_category_bias for Pace/Time priority
        dynamic_boost = place.get('solver_data', {}).get('dynamic_boost', 0.0)
        total_score += dynamic_boost
        
        # Adjust max score cap to accommodate bonuses
        return min(150.0, total_score)
    
    def _calculate_time_bias_score(self, place: Dict, current_time: datetime) -> float:
        """
        Use Lemon8's human-curated time_bias for massive accuracy boost.
        Returns 0-30 bonus points for matching time preferences.
        """
        solver_data = place.get('solver_data') or {}
        time_bias = solver_data.get('time_bias') or place.get('time_bias', 'Anytime')
        hour = current_time.hour
        
        # Massive boost for matching human-curated time bias
        if time_bias == "Morning" and 6 <= hour <= 11:
            return 30.0
        elif time_bias == "Afternoon" and 12 <= hour <= 17:
            return 30.0
        elif time_bias == "Evening" and 17 <= hour <= 23:
            return 30.0
        elif time_bias == "Late Night" and (23 <= hour or hour < 2):
            return 30.0
        elif time_bias == "Anytime":
            return 15.0  # Neutral bonus for flexible spots
        
        return 0.0
    
    def _calculate_vibe_bonus(self, place: Dict, current_time: datetime) -> float:
        """
        Time-aware vibe scoring. Certain vibes peak at certain times.
        Returns 0-20 bonus points.
        """
        hour = current_time.hour
        vibe_tags = [v.lower() for v in place.get('vibe_tags', [])]
        
        # Also check categories for vibe inference
        categories = [c.lower() for c in (place.get('categories') or place.get('types') or [])]
        all_tags = set(vibe_tags + categories)
        
        bonus = 0.0
        
        # Evening (6 PM - 11 PM): Prioritize nightlife vibes
        if 18 <= hour <= 23:
            target_vibes = {'lively', 'cocktails', 'dimly lit', 'upscale', 'bar', 'lounge', 'nightlife', 'wine'}
            matches = len(target_vibes.intersection(all_tags))
            bonus += min(20.0, matches * 5.0)
        
        # Late Night (11 PM - 2 AM): Prioritize bars and late-night spots
        elif 23 <= hour or hour < 2:
            target_vibes = {'bar', 'late night', 'nightclub', 'cocktails', '24 hours'}
            matches = len(target_vibes.intersection(all_tags))
            bonus += min(20.0, matches * 5.0)
        
        # Morning (7 AM - 11 AM): Prioritize breakfast/coffee vibes
        elif 7 <= hour <= 11:
            target_vibes = {'espresso', 'quiet', 'bakery', 'light-filled', 'cafe', 'coffee', 'breakfast', 'brunch'}
            matches = len(target_vibes.intersection(all_tags))
            bonus += min(20.0, matches * 5.0)
        
        # Afternoon (12 PM - 5 PM): Prioritize lunch and casual spots
        elif 12 <= hour <= 17:
            target_vibes = {'casual', 'lunch', 'salad', 'quick', 'sandwich', 'outdoor seating'}
            matches = len(target_vibes.intersection(all_tags))
            bonus += min(20.0, matches * 5.0)
        
        return bonus
    
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
        # - List of dicts: [{"day": 0, "hours": "7:00 AM - 9:00 PM"}, ...]
        # - Dict: {"monday": "7:00 AM - 9:00 PM", ...}
        
        current_weekday = current_time.weekday()  # 0 = Monday
        
        for hour_entry in hours:
            if isinstance(hour_entry, dict):
                day = hour_entry.get('day')
                if day == current_weekday:
                    hours_str = hour_entry.get('hours') or hour_entry.get('hours_str')
                    if hours_str:
                        # Try to parse "7:00 AM - 9:00 PM"
                        if self._parse_hours_string(hours_str, current_time_minutes):
                            return True
        
        # If can't determine, assume open (conservative)
        return True
    
    def _parse_hours_string(self, hours_str: str, current_time_minutes: int) -> bool:
        """
        Parse hours string like "7:00 AM - 9:00 PM" and check if current time is within range.
        
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
        """Extract lat/lon from place dict safely."""
        try:
            # Handle direct lat/lng keys
            lat = place.get('lat')
            lng = place.get('lng') or place.get('long')
            
            if lat is not None and lng is not None:
                return float(lat), float(lng)
                
            # Handle nested geometry/location structure
            if 'geometry' in place and 'location' in place['geometry']:
                loc = place['geometry']['location']
                lat = loc.get('lat')
                lng = loc.get('lng') or loc.get('long')
                if lat is not None and lng is not None:
                    return float(lat), float(lng)
        except (ValueError, TypeError):
            pass
            
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
        
        # Extract enriched Lemon8 data from solver_data if available
        solver_data = place.get('solver_data') or {}
        notes = place.get('notes', '')
        
        # Use human-curated notes for reason_statement (truncate for mobile UI)
        curated_reason = notes[:120].strip() if notes else None
        
        # Extract rich vibe tags, duration, and price from solver_data
        vibe_tags = solver_data.get('vibe_tags') or place.get('vibe_tags') or []
        duration_minutes = solver_data.get('duration_minutes', 60)
        price_tier = solver_data.get('price_tier') or place.get('price_tier', '$$')
        category_normalized = solver_data.get('category_normalized', '')
        time_bias = solver_data.get('time_bias') or place.get('time_bias')
        
        return {
            "name": place.get('name') or place.get('place_name') or 'Unknown',
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
            # Rich Lemon8 enriched fields
            "vibe_tags": vibe_tags[:3],  # Limit to top 3 for UI chips
            "duration_minutes": duration_minutes,
            "price_tier": price_tier,
            "category_normalized": category_normalized,
            "time_bias": time_bias,
            "curated_reason": curated_reason,  # Human notes from Lemon8
            "is_curated": place.get('is_curated', False),
        }
    
    def _bearing_to_cardinal(self, bearing: float) -> str:
        """Convert bearing in degrees to cardinal direction."""
        cardinals = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = int((bearing + 22.5) / 45.0) % 8
        return cardinals[index]
    
    def _infer_primary_vibe(self, place: Dict) -> str:
        """Infer a human-readable vibe from place data."""
        vibe_tags = place.get('vibe_tags') or []
        if vibe_tags:
            return vibe_tags[0].replace('_', ' ').capitalize()
        
        categories = place.get('categories') or place.get('types') or []
        if categories:
            cat = categories[0] if isinstance(categories[0], str) else str(categories[0])
            return cat.replace('_', ' ').capitalize()
        
        return "Local Favorite"
    
    def _infer_category(self, place: Dict) -> str:
        """
        Infer functional category (cafe, restaurant, bar, etc.) from place data.
        Used for backup selection to find operational alternatives.
        """
        categories = [c.lower() for c in (place.get('categories') or place.get('types') or [])]
        vibe_tags = [v.lower() for v in (place.get('vibe_tags') or [])]
        all_tags = set(categories + vibe_tags)
        
        # Priority-based categorization
        if any(tag in all_tags for tag in ['cafe', 'coffee', 'espresso', 'bakery', 'breakfast']):
            return 'cafe'
        elif any(tag in all_tags for tag in ['bar', 'lounge', 'cocktails', 'nightlife', 'pub']):
            return 'bar'
        elif any(tag in all_tags for tag in ['restaurant', 'dinner', 'food', 'dining']):
            return 'restaurant'
        elif any(tag in all_tags for tag in ['park', 'garden', 'outdoor', 'scenic']):
            return 'park'
        elif any(tag in all_tags for tag in ['dessert', 'ice cream', 'sweets']):
            return 'dessert'
        else:
            return 'spot'
    
    def _select_backup_option(
        self, 
        primary_place: Dict, 
        all_candidates: List[Tuple[Dict, float, float, float]]
    ) -> Optional[Dict]:
        """
        Find a 'Plan B' within 200m that matches the category or vibe of the primary.
        
        Args:
            primary_place: The primary recommended place
            all_candidates: List of (place, score, distance, vibe_bonus) tuples
        
        Returns:
            Backup option dict with name, reason, distance
        """
        if not all_candidates:
            return None
        
        primary_lat = primary_place.get('lat')
        primary_lng = primary_place.get('lng')
        if not primary_lat or not primary_lng:
            return None
        
        primary_category = self._infer_category(primary_place)
        primary_vibes = set(primary_place.get('vibe_tags', []))
        
        potential_backups = []
        
        for place, score, orig_dist, vibe_bonus in all_candidates:
            # Don't suggest the primary as its own backup
            if place.get('place_id') == primary_place.get('place_id'):
                continue
            if place.get('name') == primary_place.get('name'):
                continue
            
            place_lat, place_lng = self._extract_coordinates(place)
            if not place_lat:
                continue
            
            dist_to_primary = haversine_distance(primary_lat, primary_lng, place_lat, place_lng)
            
            # Constraint: Must be within 200m of the primary
            if dist_to_primary <= 200:
                match_score = 0
                cand_category = self._infer_category(place)
                
                # Bonus for same functional category (e.g., both are cafes)
                if cand_category == primary_category:
                    match_score += 50
                
                # Bonus for overlapping vibe tags
                cand_vibes = set(place.get('vibe_tags', []))
                match_score += len(primary_vibes.intersection(cand_vibes)) * 10
                
                # Bonus for high rating
                rating = place.get('rating') or place.get('avg_rating') or 0
                try:
                    match_score += float(rating) * 5
                except (ValueError, TypeError):
                    pass
                
                potential_backups.append((place, match_score, dist_to_primary))
        
        if not potential_backups:
            return None
        
        # Sort by match_score (desc) then distance (asc)
        potential_backups.sort(key=lambda x: (-x[1], x[2]))
        best_backup, match_score, backup_dist = potential_backups[0]
        
        # Generate reason based on match quality
        if match_score >= 50:
            reason = f"Excellent {primary_category} alternative with a similar vibe, just {int(backup_dist)}m away."
        else:
            reason = f"Nearby alternative ({int(backup_dist)}m) if {primary_place.get('name')} is busy."
        
        return {
            "name": best_backup.get('name') or 'Unknown',
            "place_id": best_backup.get('place_id'),
            "reason": reason,
            "distance_from_primary_m": int(backup_dist)
        }
    
    def _generate_reason(
        self, 
        place: Dict, 
        distance_m: float, 
        vibe_bonus: float, 
        rating: float,
        current_time: datetime
    ) -> str:
        """
        Generate a human-readable reason for recommending this place.
        PRIORITY: Use human-curated notes from Lemon8 if available.
        Falls back to template-based logic if no curated content.
        """
        # FIRST: Try to use human-curated notes from Lemon8
        # Check various possible field names for resilience
        solver_data = place.get('solver_data') or {}
        notes = (
            place.get('notes') or 
            place.get('custom_notes') or 
            place.get('description') or 
            solver_data.get('notes') or
            solver_data.get('description') or
            ''
        )
        
        if notes and isinstance(notes, str) and len(notes.strip()) > 5:
            # Use the rich, human-written description (truncate for UI)
            return notes[:160].strip() + ("..." if len(notes) > 160 else "")
        
        # FALLBACK: Generate reason from scoring components
        hour = current_time.hour
        time_label = get_time_context_label(hour)
        name = place.get('name') or 'This spot'
        
        # Prioritize by strongest signal
        if vibe_bonus >= 15:
            vibe = self._infer_primary_vibe(place)
            return f"Perfect {vibe.lower()} atmosphere for {time_label.lower()}."
        
        if distance_m <= 200:
            return f"Just {int(distance_m)}m away – ideally located on your path."
        
        if rating and rating >= 4.5:
            return f"Highly rated ({rating}★) neighborhood favorite."
        
        if distance_m <= 500:
            return f"A great option {int(distance_m)}m from your current spot."
        
        return "A top-rated spot that matches your vibe."
    
    def _generate_summary(self, step1: Dict, step2: Optional[Dict]) -> str:
        """
        Generate a narrative summary based on the category combination of steps.
        """
        if not step1:
            return "Explore the neighborhood."
        
        # Safely extract categories as strings
        s1_raw = step1.get('types') or step1.get('categories') or []
        s1_cats = [str(c).lower() for c in s1_raw if c]
        
        s1_type = 'spot'
        if any(c in s1_cats for c in ['restaurant', 'food', 'dinner']):
            s1_type = 'dinner'
        elif any(c in s1_cats for c in ['cafe', 'coffee', 'bakery']):
            s1_type = 'coffee'
        elif any(c in s1_cats for c in ['bar', 'lounge', 'nightlife']):
            s1_type = 'drinks'
        
        if not step2:
            if s1_type == 'dinner':
                return "Start with a highly-rated dinner in the neighborhood."
            elif s1_type == 'coffee':
                return "Begin your day with a great cup of coffee."
            elif s1_type == 'drinks':
                return "Kick off the evening with a lively spot."
            return "Head to a top-rated local favorite."
        
        s2_raw = step2.get('types') or step2.get('categories') or []
        s2_cats = [str(c).lower() for c in s2_raw if c]
        
        s2_type = 'spot'
        if any(c in s2_cats for c in ['bar', 'lounge', 'nightlife', 'cocktails']):
            s2_type = 'drinks'
        elif any(c in s2_cats for c in ['park', 'garden', 'outdoor']):
            s2_type = 'walk'
        elif any(c in s2_cats for c in ['dessert', 'ice cream', 'bakery']):
            s2_type = 'dessert'
        
        # Generate narrative based on combination
        combos = {
            ('dinner', 'drinks'): "Start with a highly-rated dinner, followed by a nearby spot for drinks.",
            ('coffee', 'walk'): "Enjoy a morning coffee followed by a scenic walk in the neighborhood.",
            ('dinner', 'dessert'): "A satisfying dinner followed by a sweet treat nearby.",
            ('drinks', 'drinks'): "Two great spots for an evening bar hop.",
        }
        
        return combos.get((s1_type, s2_type), 
            f"A curated {s1_type} followed by a {s2_type} just a short walk away.")
    
    def _apply_category_bias(
        self,
        places: List[Dict],
        current_time: datetime,
        step_idx: int,
        previous_stops: List[Dict]
    ) -> List[Dict]:
        """
        Apply category bias based on time of day for natural narrative arc.
        Promotes places that fit the current time context.
        
        Time Windows:
        - 06:00-11:00: Coffee, Breakfast, Bakeries, Parks
        - 12:00-14:00: Restaurants, Lunch, Cafes
        - 14:00-17:00: Museums, Shopping, Landmarks, Galleries
        - 18:00-21:00: Dinner, Bars, Nightlife, Theaters
        """
        hour = current_time.hour
        
        # Define priority categories for each time window
        priority_categories = set()
        if 6 <= hour < 11:
            priority_categories = {'cafe', 'coffee', 'breakfast', 'bakery', 'park'}
        elif 12 <= hour < 14:
            priority_categories = {'restaurant', 'lunch', 'cafe'}
        elif 14 <= hour < 17:
            priority_categories = {'museum', 'shopping', 'landmark', 'gallery', 'park'}
        elif 18 <= hour < 22:
            priority_categories = {'dinner', 'restaurant', 'bar', 'nightlife', 'theater', 'lounge'}
        else:
            # Late night / early morning - no strong bias
            return places
        
        # Get last stop's state (category + vibes)
        last_category = None
        last_vibes = set()
        if previous_stops:
            last_stop = previous_stops[-1]
            last_category = last_stop.get('category_normalized', '').lower()
            last_vibes = set(v.lower() for v in last_stop.get('vibe_tags', []))
        
        # Scored places
        scored = []
        for place in places:
            score = 0
            solver_data = place.get('solver_data') or {}
            category = solver_data.get('category_normalized', '').lower()
            vibe_tags = set(v.lower() for v in place.get('vibe_tags', []))
            
            # 1. Time Window Boost (+50)
            if category in priority_categories:
                score += 50
            
            # 2. Pace Logic Boost (+30)
            # If last stop was "Quick Service", prefer "Cozy" or "Social" to linger
            if 'quick service' in last_vibes or 'grab and go' in last_vibes:
                if 'cozy' in vibe_tags or 'social' in vibe_tags or 'lounge' in vibe_tags:
                    score += 30
            
            # 3. Penalty if same as last stop (avoid fatigue)
            if last_category and category == last_category:
                score -= 100  # Heavy penalty for consecutive duplicates
            
            # INJECT BOOST: Store score in solver_data so solve_next_action sees it
            if 'solver_data' not in place or place['solver_data'] is None:
                place['solver_data'] = {}
            
            place['solver_data']['dynamic_boost'] = score
            scored.append((place, score))
        
        # Sort by score for initial prioritization (though solve_next_action re-scores)
        scored.sort(key=lambda x: x[1], reverse=True)
        return [p for p, s in scored]
    
    def _generate_narrative_arc(self, itinerary: List[Dict], start_time: datetime) -> str:
        """
        Generate a human-readable narrative arc summary for the full day.
        Example: "Morning coffee → Museum visit → Lunch → Scenic walk → Dinner"
        """
        if not itinerary:
            return "No itinerary generated."
        
        arc_parts = []
        for stop in itinerary:
            category = stop.get('category_normalized') or self._infer_category(stop)
            arc_parts.append(category.capitalize())
        
        return " → ".join(arc_parts)


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
        steps: int = 4,
        user_preferences: Optional[Dict] = None
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
                user_preferences=user_preferences
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
