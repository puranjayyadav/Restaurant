"""
Next Best Action (NBA) Solver for real-time recommendations.
Implements rolling horizon approach - returns only the next 2 steps instead of full itinerary.
"""

from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
import math
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
        
        # --- VIBE MATCHING (Works for ALL places) ---
        # This is often MORE important than rating for date nights, work sessions, etc.
        vibe_score = 0.0
        
        # Extract place's vibe tags (handle nested structure from solver_data)
        place_vibes = (
            place.get('vibe_tags') or 
            place.get('solver_data', {}).get('vibe_tags') or 
            place.get('tags') or 
            []
        )
        place_vibes_lower = {str(v).lower() for v in place_vibes}
        
        # Also infer vibes from name/types if no explicit tags
        place_name_lower = (place.get('name') or '').lower()
        inferred_vibes = self._infer_vibes_from_place(place)
        place_vibes_lower.update(inferred_vibes)
        
        if user_preferences:
            # Support both 'vibes' (list) and 'vibe' (single)
            target_vibes = user_preferences.get('vibes') or []
            if user_preferences.get('vibe'):
                target_vibes = target_vibes + [user_preferences.get('vibe')]
            
            target_vibes_lower = [str(v).lower() for v in target_vibes]
            
            for target in target_vibes_lower:
                # Check for exact match
                if target in place_vibes_lower:
                    vibe_score += 15.0  # HUGE bonus for vibe match
                # Check for partial/fuzzy match
                elif any(target in pv or pv in target for pv in place_vibes_lower):
                    vibe_score += 8.0  # Partial match bonus
        
        total_score += vibe_score
        
        # --- CURATED BONUS ---
        # We trust our own hand-picked data more than scraped data
        if place.get('is_curated'):
            # Boost: curated places are quality-vetted
            total_score += 15.0
            
            # Source bonus: Yelp-enriched curated data is even better (has hours)
            if place.get('source') == 'yelp':
                total_score += 5.0
            
            # Time bias match (if place has optimal time and it matches)
            time_bias = place.get('time_bias') or place.get('solver_data', {}).get('time_bias')
            if time_bias:
                time_context = get_time_context_label(current_time.hour)
                if time_bias.lower() in time_context.lower() or time_context.lower() in time_bias.lower():
                    total_score += 5.0
        
        # --- CUISINE/CATEGORY PREFERENCES ---
        if user_preferences:
            # Check cuisine match
            preferred_cuisines = user_preferences.get('preferred_cuisines') or user_preferences.get('cuisines') or []
            if preferred_cuisines:
                preferred = [c.lower() for c in preferred_cuisines]
                # Check against place name and types
                place_text = place_name_lower + ' ' + ' '.join(place_types)
                if any(cuisine in place_text for cuisine in preferred):
                    total_score += 10.0
            
            # Price range preference
            if user_preferences.get('price_range'):
                place_price = place.get('price_range') or place.get('price')
                if place_price and user_preferences['price_range'] == place_price:
                    total_score += 5.0
        
        return min(100.0, total_score)
    
    def _infer_vibes_from_place(self, place: Dict) -> set:
        """
        Infer vibe tags from place name and types when explicit tags are missing.
        """
        inferred = set()
        name = (place.get('name') or '').lower()
        types = ' '.join([str(t).lower() for t in (place.get('types') or [])])
        text = name + ' ' + types
        
        # Vibe inference rules
        vibe_keywords = {
            'cozy': ['cozy', 'intimate', 'warm', 'fireplace', 'cottage'],
            'romantic': ['romantic', 'date', 'candlelit', 'intimate', 'wine bar'],
            'quiet': ['quiet', 'peaceful', 'zen', 'serene', 'calm'],
            'lively': ['lively', 'buzzing', 'energetic', 'party', 'club'],
            'trendy': ['trendy', 'hip', 'chic', 'instagram', 'aesthetic'],
            'casual': ['casual', 'laid back', 'chill', 'relaxed', 'dive'],
            'upscale': ['upscale', 'fine dining', 'luxury', 'elegant', 'michelin'],
            'family': ['family', 'kid', 'children', 'friendly'],
            'outdoor': ['outdoor', 'patio', 'rooftop', 'garden', 'terrace'],
            'hidden gem': ['hidden', 'secret', 'speakeasy', 'underground'],
            'local': ['local', 'neighborhood', 'authentic'],
            'brunch spot': ['brunch', 'weekend', 'mimosa'],
            'late night': ['late night', '24 hour', 'after hours', 'night owl'],
            'work friendly': ['wifi', 'laptop', 'workspace', 'study'],
        }
        
        for vibe, keywords in vibe_keywords.items():
            if any(kw in text for kw in keywords):
                inferred.add(vibe)
        
        return inferred
    
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
        
        Includes "Category Curfews" - common-sense rules for when places
        are likely closed even without explicit hours data.
        
        Args:
            place: Place dictionary
            current_time: Current datetime
        
        Returns:
            True if likely open, False otherwise
        """
        hours = place.get('hours') or place.get('opening_hours') or []
        current_hour = current_time.hour
        
        if not hours:
            # No hours data - apply "Category Curfews" (common sense rules)
            return self._apply_category_curfews(place, current_hour)
        
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
        
        # If can't determine from hours data, fall back to category curfews
        return self._apply_category_curfews(place, current_hour)
    
    def _apply_category_curfews(self, place: Dict, current_hour: int) -> bool:
        """
        Apply common-sense "curfews" when hours data is missing.
        
        The "Night Bloom Bug" fix: Flower markets and bakeries shouldn't
        appear as suggestions at 10 PM even if we don't have explicit hours.
        
        Args:
            place: Place dictionary
            current_hour: Current hour (0-23)
        
        Returns:
            True if place is likely open, False if likely closed
        """
        # Get all category/type info from place
        types = place.get('types') or place.get('categories') or []
        name = (place.get('name') or '').lower()
        
        # Combine types and name for checking
        category_text = ' '.join([str(t).lower() for t in types]) + ' ' + name
        
        # MORNING-ONLY places (closed after 9 PM)
        morning_keywords = ['market', 'flower', 'bakery', 'breakfast', 'brunch', 'farmer']
        if current_hour >= 21 or current_hour < 6:  # 9 PM - 6 AM
            if any(kw in category_text for kw in morning_keywords):
                return False
        
        # DAYTIME-ONLY places (closed after 10 PM)
        daytime_keywords = ['museum', 'gallery', 'park', 'garden', 'bookstore', 'library', 'shop', 'store']
        if current_hour >= 22 or current_hour < 8:  # 10 PM - 8 AM
            if any(kw in category_text for kw in daytime_keywords):
                return False
        
        # CAFE/COFFEE (typically close by 8-9 PM unless it's a bar-cafe)
        coffee_keywords = ['coffee', 'cafe', 'café', 'espresso', 'tea house']
        if current_hour >= 21 or current_hour < 6:  # 9 PM - 6 AM
            if any(kw in category_text for kw in coffee_keywords):
                # Unless it's also a bar
                if 'bar' not in category_text and 'lounge' not in category_text:
                    return False
        
        # LUNCH-ONLY places (closed after 4 PM)
        lunch_keywords = ['lunch', 'deli', 'sandwich']
        if current_hour >= 16 or current_hour < 10:  # 4 PM - 10 AM
            if any(kw in category_text for kw in lunch_keywords):
                # Unless it's a full restaurant
                if 'restaurant' not in category_text and 'dinner' not in category_text:
                    return False
        
        # LATE-NIGHT places (open late) - give them a pass
        latenight_keywords = ['bar', 'pub', 'club', 'lounge', 'late night', '24 hour', '24h']
        if any(kw in category_text for kw in latenight_keywords):
            return True
        
        # Default: assume open
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
        
        # Extract vibe_tags from place or solver_data
        vibe_tags = (
            place.get('vibe_tags') or 
            place.get('solver_data', {}).get('vibe_tags') or 
            []
        )
        solver_data = place.get('solver_data', {})
        
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
            # Vibe/preference data for UI display
            "vibe_tags": vibe_tags,
            "time_bias": solver_data.get('time_bias') or place.get('time_bias'),
            "price_tier": solver_data.get('price_tier') or place.get('price_tier'),
            "is_curated": place.get('is_curated', False),
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
    Includes "Palette Cleanser" logic to avoid category fatigue (e.g., bar-bar-bar).
    """

    # Dwell times by category (minutes)
    # Expanded to handle real-world tags like "Cookies Details", "Neighborhood", "Activity"
    DWELL_TIMES = {
        # Quick stops
        'coffee': 30,
        'cookies': 20,
        'dessert': 25,
        'bakery': 20,
        'ice cream': 20,
        'snack': 15,
        
        # Medium stops
        'cafe': 45,
        'brunch': 75,
        'lunch': 60,
        'food': 60,
        'restaurant': 75,
        'bar': 60,
        'pub': 60,
        'lounge': 60,
        
        # Long stops
        'dinner': 90,
        'fine dining': 120,
        'museum': 90,
        'gallery': 60,
        'theater': 120,
        
        # Outdoor/Activity
        'park': 45,
        'garden': 45,
        'neighborhood': 45,  # Walking around exploring
        'activity': 60,
        'shopping': 60,
        'market': 45,
        
        # Hotels/Landmarks (quick look or passing through)
        'hotel': 15,
        'landmark': 20,
        
        # Default
        'general': 45,
    }

    # Category groupings for fatigue detection
    # Expanded to handle real-world category names
    CATEGORY_GROUPS = {
        'drinking': {'bar', 'pub', 'lounge', 'night_club', 'wine_bar', 'brewery', 'cocktail', 'wine'},
        'food': {'restaurant', 'cafe', 'bakery', 'pizza', 'diner', 'fast_food', 'food', 'brunch', 'lunch', 'dinner', 'sushi', 'italian', 'mexican', 'chinese', 'thai', 'indian'},
        'coffee': {'coffee', 'tea', 'espresso'},
        'dessert': {'cookies', 'dessert', 'ice cream', 'bakery', 'patisserie', 'cake', 'pastry'},
        'culture': {'museum', 'art_gallery', 'gallery', 'theater', 'landmark', 'historical'},
        'outdoor': {'park', 'garden', 'beach', 'trail', 'neighborhood', 'market', 'flower'},
        'activity': {'activity', 'shopping', 'spa', 'gym', 'yoga', 'entertainment'},
    }

    # Palette cleanser rules: after N consecutive of group X, suggest group Y
    PALETTE_CLEANSERS = {
        'drinking': ['food', 'coffee'],  # After 2 bars, suggest food or coffee
        'food': ['coffee', 'outdoor'],    # After 2 restaurants, suggest coffee or walk
        'coffee': ['food', 'culture'],    # After 2 cafes, suggest food or museum
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
        Includes category fatigue avoidance ("Palette Cleanser" logic).
        Respects user preferences (vibes, cuisines) throughout the chain.
        """
        itinerary: List[Dict] = []
        sim_location = user_location
        sim_heading = heading
        sim_time = current_time
        used_place_ids: Set[str] = set()
        category_history: List[str] = []  # Track category sequence

        for i in range(max(1, steps)):
            # End-of-night cutoff: stop suggesting after 4 AM
            if sim_time.hour >= 4 and sim_time.hour < 6:
                break

            # Filter out already visited
            available_places = [
                p for p in places
                if (p.get('place_id') or p.get('name')) not in used_place_ids
            ]
            if not available_places:
                break

            # Palette Cleanser: check for category fatigue
            forced_categories = self._check_category_fatigue(category_history)
            if forced_categories:
                # Prefer places matching the palette cleanser categories
                preferred_places = self._filter_by_categories(available_places, forced_categories)
                if preferred_places:
                    available_places = preferred_places

            step_result = self.solve_next_action(
                user_location=sim_location,
                heading=sim_heading,
                current_time=sim_time,
                places=available_places,
                user_preferences=user_preferences  # Pass vibes/preferences through chain
            )
            best_stop = step_result.get('next_stop')
            if not best_stop:
                break

            # Infer and track category
            stop_category = self._infer_category(best_stop)
            category_group = self._get_category_group(stop_category)
            category_history.append(category_group)

            # Enrich with chain metadata
            best_stop = best_stop.copy()
            best_stop['step_sequence'] = i + 1
            best_stop['visit_context'] = get_time_context_label(sim_time.hour)
            best_stop['simulated_arrival'] = best_stop.get('estimated_arrival')
            best_stop['category'] = stop_category
            best_stop['category_group'] = category_group
            itinerary.append(best_stop)

            # Update simulation state
            place_lat, place_lon = self._extract_coordinates(best_stop)
            if place_lat is None:
                break

            distance_m = best_stop.get('distance_m') or 0
            travel_minutes = self._estimate_travel_minutes(distance_m)
            dwell_minutes = self.DWELL_TIMES.get(stop_category, 60)
            sim_time = sim_time + timedelta(minutes=travel_minutes + dwell_minutes)
            sim_location = (place_lat, place_lon)
            sim_heading = None  # allow 360° after first hop

            place_id = best_stop.get('place_id') or best_stop.get('name')
            if place_id:
                used_place_ids.add(place_id)

        return itinerary

    def _check_category_fatigue(self, history: List[str], threshold: int = 2) -> Optional[List[str]]:
        """
        Check if we've had too many consecutive stops in the same category group.
        Returns suggested palette cleanser categories, or None if no fatigue detected.
        """
        if len(history) < threshold:
            return None

        # Check last N entries for repetition
        recent = history[-threshold:]
        if len(set(recent)) == 1:  # All same category
            fatigued_group = recent[0]
            return self.PALETTE_CLEANSERS.get(fatigued_group)
        return None

    def _get_category_group(self, category: str) -> str:
        """Map a specific category to its broader group."""
        for group, members in self.CATEGORY_GROUPS.items():
            if category in members:
                return group
        return 'general'

    def _filter_by_categories(self, places: List[Dict], target_categories: List[str]) -> List[Dict]:
        """Filter places to those matching target category groups."""
        filtered = []
        for place in places:
            place_category = self._infer_category(place)
            place_group = self._get_category_group(place_category)
            if place_group in target_categories or place_category in target_categories:
                filtered.append(place)
        return filtered

    def _estimate_travel_minutes(self, distance_m: float) -> int:
        """Estimate walking travel minutes given distance (meters)."""
        walking_speed_ms = 1.39  # ~5 km/h
        seconds = distance_m / walking_speed_ms if distance_m else 0
        return max(5, int(round(seconds / 60.0)))

    def _infer_category(self, stop: Dict) -> str:
        """
        Infer a coarse category from types/name for dwell-time lookup.
        
        Handles real-world tags like "Cookies Details", "Food", "Neighborhood", "Activity".
        """
        types = stop.get('types') or stop.get('categories') or []
        name = (stop.get('name') or '').lower()
        
        # Combine all text for matching
        all_text = ' '.join([str(t).lower() for t in types]) + ' ' + name
        
        # Priority order for category detection
        # IMPORTANT: Check culture/activity FIRST because "Cookies Details" 
        # often appears in Yelp data (scraped from cookie consent banners)
        # and would incorrectly classify galleries as dessert shops
        category_keywords = [
            # HIGHEST PRIORITY: Culture/Activities (check these first!)
            ('museum', ['museum']),
            ('gallery', ['gallery', 'art gallery', 'art space']),
            ('theater', ['theater', 'theatre', 'cinema', 'playhouse']),
            ('park', ['park', 'garden', 'botanical']),
            ('market', ['market', 'flower market', 'farmer']),
            ('hotel', ['hotel', 'inn', 'motel']),
            ('landmark', ['landmark', 'monument', 'historic']),
            
            # HIGH PRIORITY: Specific food types
            ('bar', ['bar', 'pub', 'tavern', 'cocktail', 'wine bar', 'brewery']),
            ('lounge', ['lounge', 'club', 'nightclub', 'night club']),
            ('sushi', ['sushi', 'japanese', 'ramen', 'izakaya']),
            ('pizza', ['pizza', 'pizzeria']),
            ('brunch', ['brunch']),
            ('breakfast', ['breakfast']),
            ('lunch', ['lunch', 'deli', 'sandwich']),
            ('dinner', ['dinner', 'fine dining']),
            
            # MEDIUM PRIORITY: Generic categories
            ('coffee', ['coffee', 'espresso', 'roaster', 'roastery']),
            ('bakery', ['bakery', 'bread', 'croissant', 'boulangerie']),
            ('ice cream', ['ice cream', 'gelato', 'frozen yogurt']),
            ('dessert', ['dessert', 'cake', 'pastry', 'patisserie', 'sweets']),
            
            # LOWER PRIORITY: These appear in many places
            ('neighborhood', ['neighborhood', 'neighbourhood', 'walking', 'explore']),
            ('activity', ['activity', 'experience', 'tour']),
            ('shopping', ['shopping', 'shop', 'store', 'boutique']),
            ('restaurant', ['restaurant', 'bistro', 'eatery', 'kitchen', 'grill', 'trattoria']),
            ('cafe', ['cafe', 'café', 'coffeehouse']),
            ('food', ['food']),
            
            # LOWEST PRIORITY: Often from scraped artifacts
            # "Cookies Details" from cookie consent banners - check LAST
            ('cookies', ['cookies', 'cookie shop']),  # Only match if explicitly a cookie shop
        ]
        
        for category, keywords in category_keywords:
            if any(kw in all_text for kw in keywords):
                return category
        
        # Default fallback
        return 'general'

