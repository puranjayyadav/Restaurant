"""
Day Planner Service - Centralized API for generating full-day itineraries
"""
import math
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from supabase_config import get_supabase_client
from .utils import haversine_distance
from .hybrid_search_service import HybridSearchService


class TimeSlotEngine:
    """Manages time slots for a full day itinerary"""
    
    SLOTS = [
        {"name": "coffee", "start": 7, "end": 10, "categories": ["coffee", "cafe", "bakery", "breakfast"]},
        {"name": "activity", "start": 10, "end": 12, "categories": ["park", "museum", "gallery", "bookstore", "shopping"]},
        {"name": "brunch", "start": 12, "end": 14, "categories": ["restaurant", "brunch", "cafe"]},
        {"name": "afternoon", "start": 14, "end": 17, "categories": ["park", "bookstore", "museum", "gallery", "activity"]},
        {"name": "lunch", "start": 12, "end": 15, "categories": ["restaurant", "lunch", "food"]},
        {"name": "dinner", "start": 18, "end": 21, "categories": ["restaurant", "dinner", "fine_dining"]},
        {"name": "nightlife", "start": 21, "end": 24, "categories": ["bar", "nightclub", "lounge", "speakeasy"]},
    ]
    
    @staticmethod
    def get_slot_for_time(hour: int) -> str:
        """Get the appropriate slot name for a given hour"""
        for slot in TimeSlotEngine.SLOTS:
            if slot["start"] <= hour < slot["end"]:
                return slot["name"]
        return "activity"  # Default
    
    @staticmethod
    def get_all_slots() -> List[str]:
        """Get all slot names in order"""
        return [slot["name"] for slot in TimeSlotEngine.SLOTS]
    
    @staticmethod
    def get_time_for_slot(slot_name: str, start_hour: int = 10) -> str:
        """Get formatted time string for a slot"""
        slot_map = {
            "coffee": 7,
            "activity": 10,
            "brunch": 12,
            "lunch": 13,
            "afternoon": 14,
            "dinner": 19,
            "nightlife": 21,
        }
        hour = slot_map.get(slot_name, start_hour)
        am_pm = "AM" if hour < 12 else "PM"
        hour_12 = hour if hour <= 12 else hour - 12
        if hour_12 == 0:
            hour_12 = 12
        return f"{hour_12}:00 {am_pm}"


class DayPlannerService:
    """Main service for generating day itineraries"""
    
    # Social context mappings
    SOCIAL_CONTEXT_VIBES = {
        "couple": ["dinner_date", "romantic", "speakeasy", "fine_dining"],
        "solo": ["solo_date", "work_friendly", "coffee", "coffee_run"],
        "group": ["dinner_group", "brunch_buzzy", "casual_lunch"],
        "family": ["casual_lunch", "breakfast_classic", "family_friendly"],
    }
    
    SOCIAL_CONTEXT_COUNTS = {
        "couple": (4, 5),
        "solo": (3, 4),
        "group": (5, 6),
        "family": (4, 5),
    }
    
    # NYC bounds for random location generation
    NYC_BOUNDS = {
        'min_lat': 40.4774,  # Southernmost point (Staten Island)
        'max_lat': 40.9176,  # Northernmost point (Bronx)
        'min_lon': -74.2591,  # Westernmost point (New Jersey border)
        'max_lon': -73.7004,  # Easternmost point (Queens)
    }
    NYC_CENTER = (40.7128, -74.0060)  # Manhattan center (fallback)
    
    # STRICT chain blacklist - exclude all recognizable chains
    CHAIN_BLACKLIST = [
        # Coffee chains
        'starbucks', 'dunkin', 'dunkin donuts', 'tim hortons', 'peet\'s coffee',
        'caribou coffee', 'costa coffee', 'the coffee bean',
        
        # Fast food
        'mcdonald\'s', 'mcdonalds', 'burger king', 'wendy\'s', 'wendys',
        'taco bell', 'kfc', 'popeyes', 'chick-fil-a', 'chipotle',
        'panera bread', 'subway', 'jimmy john\'s', 'jersey mike\'s',
        'five guys', 'shake shack', 'in-n-out', 'whataburger',
        
        # Casual dining chains
        'applebee\'s', 'chili\'s', 'olive garden', 'red lobster',
        'outback steakhouse', 'texas roadhouse', 'buffalo wild wings',
        'cheesecake factory', 'p.f. chang\'s',
        
        # Pizza chains
        'domino\'s', 'pizza hut', 'papa john\'s', 'little caesars',
        
        # Existing exclusions (keep these)
        'grocery', 'market', 'pharmacy', 'gas station', 'convenience',
        'dollar store', 'supermarket', 'warehouse', 'wholesale',
        'bank', 'atm', 'insurance', 'dentist', 'doctor', 'clinic',
        'post office', 'ups store', 'fedex', 'dry cleaner',
        'target', 'walmart', 'costco', 'sam\'s club', 'home depot', 'lowes',
        'lumber', 'hardware', 'drug store', 'auto', 'car wash', 'mechanic',
        'repair', 'tire', 'credit union', 'real estate', 'lawyer',
        'hospital', 'veterinary', 'vet', 'shipping', 'laundromat',
        'storage', 'moving', 'furniture store'
    ]
    
    # Curated list of NYC neighborhoods/areas with good venue coverage
    # These are known areas where we have substantial venue data
    NYC_VENUE_RICH_LOCATIONS = [
        # Manhattan
        (40.7580, -73.9855),  # Times Square / Midtown West
        (40.7505, -73.9934),  # Midtown East
        (40.7614, -73.9776),  # Central Park South
        (40.7282, -73.9942),  # Greenwich Village
        (40.7359, -73.9911),  # SoHo
        (40.7489, -73.9680),  # Upper East Side
        (40.7831, -73.9712),  # Upper West Side
        (40.7282, -73.9848),  # West Village
        (40.7614, -73.9776),  # Lincoln Center
        (40.7505, -73.9934),  # Grand Central
        (40.7589, -73.9851),  # Theater District
        (40.7282, -73.9942),  # NYU / Washington Square
        # Brooklyn
        (40.6782, -73.9442),  # Williamsburg
        (40.6892, -73.9442),  # Greenpoint
        (40.6782, -73.9942),  # DUMBO
        (40.6501, -73.9496),  # Park Slope
        (40.6862, -73.9772),  # Brooklyn Heights
        (40.6782, -73.9442),  # Bushwick
        (40.6501, -73.9496),  # Prospect Heights
        (40.6782, -73.9942),  # Brooklyn Bridge area
        # Queens
        (40.7489, -73.9370),  # Long Island City
        (40.7282, -73.7949),  # Astoria
        (40.7282, -73.9370),  # Sunnyside
        # Bronx
        (40.8506, -73.9264),  # South Bronx / Port Morris
        # Staten Island (limited but included)
        (40.6415, -74.0776),  # St. George / Ferry area
    ]
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def _get_random_nyc_location(self) -> Tuple[float, float]:
        """
        Generate a random location from curated NYC neighborhoods with good venue coverage.
        This ensures we always pick areas where we have substantial venue data.
        """
        import random
        # Select a random neighborhood from our curated list
        base_lat, base_lon = random.choice(self.NYC_VENUE_RICH_LOCATIONS)
        
        # Add a small random offset (200m-800m) to provide variety within the neighborhood
        # This ensures different results even when the same neighborhood is selected
        offset_distance_m = random.uniform(200, 800)
        offset_bearing_deg = random.uniform(0, 360)
        offset_bearing_rad = math.radians(offset_bearing_deg)
        
        # Convert offset to lat/lon delta
        lat_offset_km = (offset_distance_m / 1000) * math.cos(offset_bearing_rad)
        lon_offset_km = (offset_distance_m / 1000) * math.sin(offset_bearing_rad) / math.cos(math.radians(base_lat))
        
        # Convert km to degrees
        lat_offset = lat_offset_km / 111.0
        lon_offset = lon_offset_km / 111.0
        
        # Apply offset
        randomized_lat = base_lat + lat_offset
        randomized_lon = base_lon + lon_offset
        
        # Ensure still within NYC bounds (clamp if needed)
        randomized_lat = max(self.NYC_BOUNDS['min_lat'], min(self.NYC_BOUNDS['max_lat'], randomized_lat))
        randomized_lon = max(self.NYC_BOUNDS['min_lon'], min(self.NYC_BOUNDS['max_lon'], randomized_lon))
        
        return randomized_lat, randomized_lon
    
    def _add_random_offset(self, lat: float, lon: float, min_distance_m: int = 100, max_distance_m: int = 400) -> Tuple[float, float]:
        """
        Add a random offset to coordinates (same logic as geocode-location).
        This provides variety when the same location is used multiple times.
        
        Args:
            lat: Base latitude
            lon: Base longitude
            min_distance_m: Minimum offset distance in meters (default 500m)
            max_distance_m: Maximum offset distance in meters (default 2000m)
        
        Returns:
            Tuple of (randomized_lat, randomized_lon)
        """
        import random
        import math
        
        # Generate random offset (500m - 2km radius) for variety
        offset_distance_m = random.uniform(min_distance_m, max_distance_m)
        offset_bearing_deg = random.uniform(0, 360)  # Random direction in degrees
        offset_bearing_rad = math.radians(offset_bearing_deg)
        
        # Convert offset to lat/lon delta using bearing
        # 1 degree latitude ≈ 111km, 1 degree longitude ≈ 111km * cos(latitude)
        lat_offset_km = (offset_distance_m / 1000) * math.cos(offset_bearing_rad)
        lon_offset_km = (offset_distance_m / 1000) * math.sin(offset_bearing_rad) / math.cos(math.radians(lat))
        
        # Convert km to degrees
        lat_offset = lat_offset_km / 111.0
        lon_offset = lon_offset_km / 111.0
        
        # Apply offset
        randomized_lat = lat + lat_offset
        randomized_lon = lon + lon_offset
        
        return randomized_lat, randomized_lon
    
    def generate_itinerary(
        self,
        start_lat: Optional[float] = None,
        start_long: Optional[float] = None,
        selected_vibe: Optional[str] = None,
        social_context: str = "couple",
        radius_meters: int = 3000,
        local_time_start: str = "10:00",
        cuisine_preferences: Optional[List[str]] = None,
        cuisine_preference_min: Optional[int] = None,
        cuisine_preference_max: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Generate a full-day itinerary
        
        Args:
            start_lat: Starting latitude (optional, defaults to random NYC location)
            start_long: Starting longitude (optional, defaults to random NYC location)
            selected_vibe: Optional vibe slug to filter by
            social_context: couple, solo, group, or family
            radius_meters: Search radius in meters
            local_time_start: Start time in HH:MM format
        
        Returns:
            Dict with itinerary, hidden_gems_injected, total_walk_time_mins, narrative
        """
        if not self.supabase:
            return {"error": "Supabase client not available"}
        
        # Get user's excluded venues from history
        excluded_from_history = []
        history_service = None
        if user_id:
            from .user_history_service import UserHistoryService
            history_service = UserHistoryService()
            excluded_from_history = history_service.get_excluded_place_ids(user_id, days_back=30)
            print(f"DEBUG: Excluding {len(excluded_from_history)} venues from user history")
        
        # Parse start time
        try:
            hour, minute = map(int, local_time_start.split(":"))
            start_hour = hour
        except:
            start_hour = 10
        
        # Use random NYC location if coordinates not provided
        original_coords_provided = start_lat is not None and start_long is not None
        if not start_lat or not start_long:
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
                        'location': 'day_planner_service.py:169',
                        'message': 'No coordinates provided, generating random NYC location',
                        'data': {
                            'start_lat_received': start_lat,
                            'start_long_received': start_long
                        },
                        'timestamp': int(__import__('time').time() * 1000)
                    }) + '\n')
            except: pass
            # #endregion
            start_lat, start_long = self._get_random_nyc_location()
            print(f"DEBUG: Using random NYC location: ({start_lat:.4f}, {start_long:.4f})")
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'sessionId': 'debug-session',
                        'runId': 'run1',
                        'hypothesisId': 'A',
                        'location': 'day_planner_service.py:175',
                        'message': 'Random NYC location generated',
                        'data': {
                            'random_lat': start_lat,
                            'random_lon': start_long
                        },
                        'timestamp': int(__import__('time').time() * 1000)
                    }) + '\n')
            except: pass
            # #endregion
        else:
            # Add random offset to provided coordinates for variety (same as geocode-location)
            # This ensures different results even when same filter coordinates are used
            original_lat, original_lon = start_lat, start_long
            start_lat, start_long = self._add_random_offset(start_lat, start_long)
            print(f"DEBUG: Added random offset to coordinates: ({original_lat:.4f}, {original_lon:.4f}) → ({start_lat:.4f}, {start_long:.4f})")
        
        # Target 7 places total
        target_stops = 7
        
        # Map "romantic" to "dinner_date" if it's not a valid vibe_slug
        vibe_mapping = {
            "romantic": "dinner_date",
            "romance": "dinner_date",
        }
        final_vibe = vibe_mapping.get(selected_vibe, selected_vibe) if selected_vibe else None
        
        # Retry mechanism: if no venues found and we used a random location, try different locations
        max_retries = 3 if not original_coords_provided else 0  # Only retry if coordinates were randomly generated
        retry_count = 0
        all_venues = []
        
        # #region agent log
        import json
        import os
        log_path = r'c:\Users\PURANJAY\OneDrive\Documents\Res_2\.cursor\debug.log'
        # #endregion
        
        while retry_count <= max_retries and not all_venues:
            if retry_count > 0:
                # Try a different random location
                start_lat, start_long = self._get_random_nyc_location()
                print(f"DEBUG: Retry {retry_count}: Trying different NYC location: ({start_lat:.4f}, {start_long:.4f})")
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            'sessionId': 'debug-session',
                            'runId': 'run1',
                            'hypothesisId': 'A',
                            'location': 'day_planner_service.py:280',
                            'message': f'Retry {retry_count}: Trying different location',
                            'data': {
                                'retry_count': retry_count,
                                'retry_lat': start_lat,
                                'retry_lon': start_long
                            },
                            'timestamp': int(__import__('time').time() * 1000)
                        }) + '\n')
                except: pass
                # #endregion
            
            # Fetch filtered venues (with vibe/cuisine preferences) - limit to max 3
            filtered_venues = self._fetch_venues(
                start_lat, start_long, radius_meters, final_vibe,
                cuisine_preferences=cuisine_preferences,
                cuisine_preference_min=cuisine_preference_min,
                cuisine_preference_max=cuisine_preference_max,
                excluded_place_ids=excluded_from_history
            )
            
            # Inject hidden gems (1-2 entries) that match filters
            hidden_gems = self._fetch_hidden_gems(
                start_lat, start_long, radius_meters, final_vibe,
                cuisine_preferences=cuisine_preferences,
                excluded_place_ids=excluded_from_history
            )
            gems_injected = min(2, len(hidden_gems))
            
            # Combine filtered venues and hidden gems, deduplicating by place_id
            combined_venues = filtered_venues + hidden_gems[:gems_injected]
            seen_place_ids = set()
            deduplicated_venues = []
            duplicates_found = 0
            for venue in combined_venues:
                place_id = venue.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    deduplicated_venues.append(venue)
                elif place_id:
                    duplicates_found += 1
                    print(f"DEBUG: Duplicate venue detected (place_id: {place_id}, name: {venue.get('name', 'Unknown')})")
            
            if duplicates_found > 0:
                print(f"DEBUG: Removed {duplicates_found} duplicate venues from filtered_venues + hidden_gems")
            
            # Limit to max 3 filtered venues (including hidden gems)
            filtered_venues_limited = deduplicated_venues[:3]
            
            # Fetch diverse venues for remaining slots (coffee, parks, bookstores, other restaurants)
            # Exclude place_ids already in filtered_venues_limited
            exclude_place_ids = [v.get("place_id") for v in filtered_venues_limited if v.get("place_id")]
            diverse_venues = self._fetch_diverse_venues(
                start_lat, start_long, radius_meters,
                exclude_place_ids=exclude_place_ids
            )
            
            # Combine: max 3 filtered venues + diverse venues to reach 7 total
            # Deduplicate again to ensure no duplicates between filtered and diverse venues
            all_venues = filtered_venues_limited.copy()
            seen_place_ids = set([v.get("place_id") for v in filtered_venues_limited if v.get("place_id")])
            diverse_duplicates = 0
            for venue in diverse_venues:
                place_id = venue.get("place_id")
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    all_venues.append(venue)
                elif place_id:
                    diverse_duplicates += 1
                    print(f"DEBUG: Duplicate venue in diverse_venues (place_id: {place_id}, name: {venue.get('name', 'Unknown')})")
            
            if diverse_duplicates > 0:
                print(f"DEBUG: Removed {diverse_duplicates} duplicate venues from diverse_venues")
            
            print(f"DEBUG: Final all_venues count: {len(all_venues)} (unique place_ids: {len(seen_place_ids)})")
            
            if not all_venues:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"DEBUG: No venues found at location ({start_lat:.4f}, {start_long:.4f}), retrying...")
                    continue
        
        if not all_venues:
            return {"error": "No venues found in the specified area after trying multiple locations"}
        
        # Build itinerary using time slots (7 places total)
        itinerary = self._build_itinerary(all_venues, start_lat, start_long, start_hour, target_stops)
        
        # Ensure at least one hidden gem is included
        has_hidden_gem = any(item.get("is_hidden_gem", False) for item in itinerary)
        if not has_hidden_gem and hidden_gems:
            # Force at least one hidden gem into the itinerary
            # Find the best slot to insert it (prefer middle slots)
            gem = hidden_gems[0]
            if len(itinerary) > 0:
                # Create a venue lookup map
                venue_map = {v.get("place_id"): v for v in all_venues if v.get("place_id")}
                
                # Insert at a middle position (around index 3-4)
                insert_index = min(3, len(itinerary) - 1)
                current_item = itinerary[insert_index]
                
                # Calculate distance from previous item
                # Get previous venue's location from venue_map
                prev_lat, prev_lon = start_lat, start_long
                if insert_index > 0:
                    prev_place_id = itinerary[insert_index - 1].get("place_id")
                    if prev_place_id and prev_place_id in venue_map:
                        prev_venue = venue_map[prev_place_id]
                        prev_lat = float(prev_venue.get("latitude", start_lat))
                        prev_lon = float(prev_venue.get("longitude", start_long))
                
                try:
                    dist = haversine_distance(
                        prev_lat, prev_lon,
                        float(gem["latitude"]), float(gem["longitude"])
                    )
                except (ValueError, TypeError):
                    dist = 500  # Default distance
                
                # Create itinerary item for hidden gem
                gem_item = {
                    "slot": current_item.get("slot", "afternoon"),
                    "time": current_item.get("time", "14:00"),
                    "place_id": gem["place_id"],
                    "name": gem.get("name", "Unknown"),
                    "vibe_match": self._calculate_vibe_match(gem, current_item.get("slot", "afternoon")),
                    "distance_m": int(dist),
                    "is_hidden_gem": True,
                    "latitude": float(gem.get("latitude", 0)),
                    "longitude": float(gem.get("longitude", 0)),
                    "phone": gem.get("phone"),
                    "website": gem.get("website")
                }
                
                # Insert the hidden gem
                itinerary.insert(insert_index, gem_item)
                # Remove last item if we exceed target_stops
                if len(itinerary) > target_stops:
                    itinerary = itinerary[:target_stops]
        
        # Calculate total walk time
        total_walk_time = self._calculate_walk_time(itinerary)
        
        # Generate narrative
        narrative = self._generate_narrative(itinerary, selected_vibe, social_context)
        
        # Save itinerary to user history
        if user_id and history_service and itinerary:
            import uuid
            place_ids = [stop.get('place_id') for stop in itinerary if stop.get('place_id')]
            if place_ids:
                history_service.save_itinerary_history(
                    user_id=user_id,
                    itinerary_id=str(uuid.uuid4()),
                    place_ids=place_ids,
                    filters={
                        'cuisine': cuisine_preferences,
                        'vibe': selected_vibe,
                        'social_context': social_context,
                        'radius': radius_meters
                    }
                )
                print(f"DEBUG: Saved {len(place_ids)} venues to user history")
        
        return {
            "itinerary": itinerary,
            "hidden_gems_injected": gems_injected,
            "total_walk_time_mins": total_walk_time,
            "narrative": narrative
        }
    
    def _fetch_venues(
        self,
        lat: float,
        lon: float,
        radius_meters: int,
        vibe_slug: Optional[str] = None,
        cuisine_preferences: Optional[List[str]] = None,
        cuisine_preference_min: Optional[int] = None,
        cuisine_preference_max: Optional[int] = None,
        excluded_place_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Fetch venues using hybrid search (semantic + vibe + insights)."""
        try:
            # Build search query from vibe and cuisine
            query_parts = []
            if vibe_slug:
                vibe_mapping = {
                    "dinner_date": "romantic dinner restaurant candlelit cozy atmosphere",
                    "work_friendly": "laptop friendly coffee shop wifi outlets",
                    "coffee_run": "specialty coffee roasters espresso bar",
                    "speakeasy": "hidden speakeasy bar entrance behind bookshelf",
                    "brunch_buzzy": "popular brunch spot avocado toast bottomless mimosas",
                    "casual_lunch": "casual lunch spot sandwiches salads fast casual",
                    "fine_dining": "upscale fine dining tasting menu michelin guide",
                    "solo_date": "restaurant with bar seating for solo dining",
                    "breakfast_classic": "classic breakfast diner pancakes eggs bacon",
                    "late_night_eats": "late night food open late pizza tacos burgers",
                }
                query_parts.append(vibe_mapping.get(vibe_slug, vibe_slug))
            
            if cuisine_preferences:
                cuisine_mapping = {
                    "indian_north": "butter chicken tandoori naan Indian",
                    "indian_south": "dosa idli sambar vegetarian spicy chettinad",
                    "korean_bbq": "korean bbq galbi bulgogi ktown",
                    "japanese_sushi": "sushi omakase fresh fish",
                    "japanese_izakaya": "yakitori skewers ramen small plates sake",
                    "chinese_sichuan": "ma la peppercorn mapo tofu spicy",
                    "italian_red_sauce": "italian american chicken parm meatballs",
                    "mexican_street": "tacos al pastor street cart elote",
                    "vietnamese": "pho beef noodle soup banh mi",
                    "thai_isan": "northeast thai spicy papaya salad larb",
                    "french_bistro": "steak frites onion soup escargots",
                    "pizza_nyc": "classic new york slice thin crust coal oven",
                }
                for cuisine in cuisine_preferences:
                    query_parts.append(cuisine_mapping.get(cuisine, cuisine))
            
            search_query = " ".join(query_parts) if query_parts else "great restaurants"
            
            # Perform hybrid search
            hybrid_service = HybridSearchService()
            results = hybrid_service.search(
                query=search_query,
                vibe_slugs=[vibe_slug] if vibe_slug else [],
                cuisine_slugs=cuisine_preferences or [],
                lat=lat,
                lng=lon,
                radius_km=radius_meters / 1000.0,
                limit=100
            )
            
            # Convert hybrid search results to venue format
            filtered_venues = []
            excluded_set = set(excluded_place_ids) if excluded_place_ids else set()
            
            for result in results:
                # Exclude venues from user history
                place_id = result.get("place_id")
                if place_id and place_id in excluded_set:
                    continue
                
                # Quality filters - use comprehensive chain blacklist
                name_lower = (result.get("name") or "").lower()
                if any(keyword in name_lower for keyword in self.CHAIN_BLACKLIST):
                    continue
                
                # Minimum rating filter
                rating = result.get("rating") or 0
                if rating < 4.0:
                    continue
                
                # Calculate distance
                if result.get("latitude") and result.get("longitude"):
                    try:
                        dist = haversine_distance(lat, lon, float(result["latitude"]), float(result["longitude"]))
                        if dist <= radius_meters:
                            venue = {
                                "place_id": result.get("place_id"),
                                "name": result.get("name"),
                                "address": result.get("address"),
                                "latitude": result.get("latitude"),
                                "longitude": result.get("longitude"),
                                "rating": result.get("rating"),
                                "review_count": result.get("review_count"),
                                "distance_m": dist,
                                "semantic_score": result.get("semantic_score", 0.0),
                                "vibe_match_score": result.get("vibe_match_score", 0.0),
                                "insight_score": result.get("insight_score", 0.0),
                                "final_score": result.get("final_score", 0.0),
                                "matched_vibes": result.get("matched_vibes", []),
                            }
                            
                            # Add cuisine match scoring
                            if cuisine_preferences:
                                matched_vibes = set(result.get("matched_vibes", []))
                                cuisine_set = set(cuisine_preferences)
                                matches = cuisine_set.intersection(matched_vibes)
                                venue['cuisine_match_score'] = len(matches)
                                venue['has_cuisine_match'] = len(matches) > 0
                                venue['cuisine_matches'] = list(matches)
                            else:
                                venue['cuisine_match_score'] = 0
                                venue['has_cuisine_match'] = False
                            
                            filtered_venues.append(venue)
                    except (ValueError, TypeError):
                        continue
            
            # Add randomization for variety - shuffle within quality groups
            # Separate into cuisine-matching and non-matching
            cuisine_matching = [v for v in filtered_venues if v.get("has_cuisine_match", False)]
            non_matching = [v for v in filtered_venues if not v.get("has_cuisine_match", False)]
            
            # Shuffle both groups for variety
            random.shuffle(cuisine_matching)
            random.shuffle(non_matching)
            
            # Within cuisine-matching, sort by cuisine score (higher = better match)
            # but add small random factor to prevent same order every time
            for v in cuisine_matching:
                v['_random_factor'] = random.random() * 0.3  # Small random boost
            
            cuisine_matching.sort(key=lambda v: (
                -(v.get("cuisine_match_score", 0) + v['_random_factor']),  # Cuisine match + random
                -(v.get("rating") or 0)  # Higher rating
            ))
            
            # Within non-matching, sort by rating with random factor
            for v in non_matching:
                v['_random_factor'] = random.random() * 0.5
            
            non_matching.sort(key=lambda v: (
                -((v.get("rating") or 0) + v['_random_factor'])
            ))
            
            # Combine: cuisine-matching venues first (for filter priority), then others
            # This ensures majority of selected venues match the cuisine filter
            filtered_venues = cuisine_matching + non_matching
            
            # Clean up temporary field
            for v in filtered_venues:
                v.pop('_random_factor', None)
            
            # Apply cuisine preference limits
            if cuisine_preferences and cuisine_preference_min is not None and len(filtered_venues) > 0:
                matching_venues = [v for v in filtered_venues if v.get("cuisine_match_score", 0) >= cuisine_preference_min]
                if len(matching_venues) >= 3:
                    filtered_venues = matching_venues
            
            if cuisine_preferences and cuisine_preference_max is not None:
                filtered_venues = [v for v in filtered_venues if v.get("cuisine_match_score", 0) <= cuisine_preference_max]
            
            print(f"DEBUG: Returning {len(filtered_venues)} venues ({len(cuisine_matching)} cuisine-match, {len(non_matching)} diverse)")
            return filtered_venues[:100]  # Return top 100 for selection
            
        except Exception as e:
            print(f"Error fetching venues with hybrid search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_hidden_gems(
        self,
        lat: float,
        lon: float,
        radius_meters: int,
        vibe_slug: Optional[str] = None,
        cuisine_preferences: Optional[List[str]] = None,
        excluded_place_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Fetch 1-2 hidden gems from hidden_gems_v2"""
        try:
            query = self.supabase.table("hidden_gems_v2").select("*").limit(200)
            
            # Filter by vibe if specified
            if vibe_slug:
                query = query.eq("vibe_slug", vibe_slug)
            # Note: hidden_gems_v2 has vibe_slug field, so cuisine preferences are handled via vibe_slug
            # If cuisine preferences are provided, we could filter by matching vibe_slug
            elif cuisine_preferences and len(cuisine_preferences) > 0:
                # Use first cuisine preference as vibe filter for hidden gems
                query = query.eq("vibe_slug", cuisine_preferences[0])
            
            result = query.execute()
            gems = result.data if result.data else []
            
            # Filter by distance and quality
            filtered_gems = []
            excluded_set = set(excluded_place_ids) if excluded_place_ids else set()
            for gem in gems:
                if gem.get("latitude") and gem.get("longitude"):
                    try:
                        # Exclude venues from user history
                        place_id = gem.get("place_id")
                        if place_id and place_id in excluded_set:
                            continue
                        
                        # Quality filters - use comprehensive chain blacklist
                        name_lower = (gem.get("name") or "").lower()
                        if any(keyword in name_lower for keyword in self.CHAIN_BLACKLIST):
                            continue
                        
                        # Minimum rating filter
                        rating = gem.get("rating") or 0
                        if rating < 4.0:
                            continue
                        
                        dist = haversine_distance(lat, lon, float(gem["latitude"]), float(gem["longitude"]))
                        if dist <= radius_meters:
                            gem["distance_m"] = dist
                            gem["is_hidden_gem"] = True
                            filtered_gems.append(gem)
                    except (ValueError, TypeError):
                        continue  # Skip gems with invalid coordinates
            
            # Sort by rating (descending)
            filtered_gems.sort(key=lambda g: -(g.get("rating") or 0))
            
            return filtered_gems[:2]  # Return top 2
            
        except Exception as e:
            print(f"Error fetching hidden gems: {e}")
            return []
    
    def _fetch_diverse_venues(
        self,
        lat: float,
        lon: float,
        radius_meters: int,
        exclude_place_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Fetch diverse venue types: coffee, parks, bookstores, other restaurants"""
        try:
            exclude_set = set(exclude_place_ids) if exclude_place_ids else set()
            
            # Define diverse vibe slugs for different venue types
            diverse_vibes = [
                "coffee", "coffee_run",  # Coffee shops
                "brunch_buzzy", "casual_lunch",  # Other restaurants
            ]
            
            diverse_place_ids = set()
            
            # Fetch venues with diverse vibes
            for vibe in diverse_vibes:
                try:
                    result = self.supabase.table("venue_vibes").select("place_id").eq("vibe_slug", vibe).limit(200).execute()
                    if result.data:
                        for v in result.data:
                            place_id = v.get("place_id")
                            if place_id and place_id not in exclude_set:
                                diverse_place_ids.add(place_id)
                except Exception as e:
                    print(f"Error fetching diverse vibe {vibe}: {e}")
                    continue
            
            diverse_place_ids = list(diverse_place_ids)[:100]  # Limit to 100 for performance
            
            # Fetch venue details
            venues = []
            if diverse_place_ids:
                batch_size = 100
                for i in range(0, min(len(diverse_place_ids), 100), batch_size):
                    batch_ids = diverse_place_ids[i:i+batch_size]
                    try:
                        result = self.supabase.table("venues").select("*").in_("place_id", batch_ids).execute()
                        if result.data:
                            venues.extend(result.data)
                    except Exception as e:
                        print(f"Error fetching diverse venues batch: {e}")
                        continue
            
            # Also fetch venues that might be parks, bookstores by name/category
            if len(venues) < 10:
                try:
                    result = self.supabase.table("venues").select("*").limit(500).execute()
                    if result.data:
                        keywords = ['park', 'bookstore', 'cafe', 'coffee', 'bakery', 'bistro']
                        for venue in result.data:
                            place_id = venue.get("place_id")
                            if place_id and place_id not in exclude_set:
                                name_lower = (venue.get("name") or "").lower()
                                categories = venue.get("categories", [])
                                categories_str = " ".join([str(c).lower() for c in categories])
                                
                                if any(keyword in name_lower or keyword in categories_str for keyword in keywords):
                                    venues.append(venue)
                except Exception as e:
                    print(f"Error fetching additional diverse venues: {e}")
            
            # Filter by distance and quality
            filtered_venues = []
            for venue in venues:
                if venue.get("latitude") and venue.get("longitude"):
                    try:
                        place_id = venue.get("place_id")
                        if place_id in exclude_set:
                            continue
                        
                        # Quality filters - use comprehensive chain blacklist
                        name_lower = (venue.get("name") or "").lower()
                        if any(keyword in name_lower for keyword in self.CHAIN_BLACKLIST):
                            continue
                        
                        rating = venue.get("rating") or 0
                        if rating < 4.0:
                            continue
                        
                        dist = haversine_distance(lat, lon, float(venue["latitude"]), float(venue["longitude"]))
                        if dist <= radius_meters:
                            venue["distance_m"] = dist
                            filtered_venues.append(venue)
                    except (ValueError, TypeError):
                        continue
            
            # Shuffle for variety, then sort by rating with random factor
            random.shuffle(filtered_venues)
            for v in filtered_venues:
                v['_random_factor'] = random.random() * 0.5
            filtered_venues.sort(key=lambda v: (
                -((v.get("rating") or 0) + v['_random_factor'])
            ))
            for v in filtered_venues:
                v.pop('_random_factor', None)
            
            return filtered_venues[:10]  # Return top 10 for selection
            
        except Exception as e:
            print(f"Error fetching diverse venues: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _build_itinerary(
        self,
        venues: List[Dict],
        start_lat: float,
        start_lon: float,
        start_hour: int,
        target_stops: int
    ) -> List[Dict]:
        """Build itinerary by assigning venues to time slots"""
        itinerary = []
        used_place_ids = set()
        current_lat, current_lon = start_lat, start_lon
        current_hour = start_hour
        
        # Define slot order (always full day regardless of start time)
        slot_order = ["coffee", "activity", "brunch", "afternoon", "lunch", "dinner", "nightlife"]
        
        # Start from appropriate slot based on time
        slot_index = 0
        if start_hour >= 21:
            slot_index = 6  # Start at nightlife
        elif start_hour >= 18:
            slot_index = 5  # Start at dinner
        elif start_hour >= 14:
            slot_index = 3  # Start at afternoon
        elif start_hour >= 12:
            slot_index = 2  # Start at brunch
        elif start_hour >= 10:
            slot_index = 1  # Start at activity
        else:
            slot_index = 0  # Start at coffee
        
        slots_used = 0
        for i in range(len(slot_order)):
            if slots_used >= target_stops:
                break
            
            slot_name = slot_order[(slot_index + i) % len(slot_order)]
            
            # Find best venue for this slot
            venue = self._select_venue_for_slot(
                venues, slot_name, current_lat, current_lon, used_place_ids
            )
            
            if venue:
                place_id = venue.get("place_id")
                # Double-check place_id is valid and not already used (defensive check)
                if not place_id or place_id in used_place_ids:
                    continue
                
                # Calculate distance from current location
                try:
                    dist = haversine_distance(
                        current_lat, current_lon,
                        float(venue["latitude"]), float(venue["longitude"])
                    )
                except (ValueError, TypeError):
                    continue  # Skip venues with invalid coordinates
                
                # Get time for this slot
                time_str = TimeSlotEngine.get_time_for_slot(slot_name, current_hour)
                
                # Calculate vibe match score if vibe was specified
                vibe_match = self._calculate_vibe_match(venue, slot_name)
                
                itinerary.append({
                    "slot": slot_name,
                    "time": time_str,
                    "place_id": place_id,
                    "name": venue.get("name", "Unknown"),
                    "vibe_match": vibe_match,
                    "distance_m": int(dist),
                    "is_hidden_gem": venue.get("is_hidden_gem", False),
                    "latitude": float(venue.get("latitude", 0)),
                    "longitude": float(venue.get("longitude", 0)),
                    "rating": venue.get("rating") or 0,
                    "review_count": venue.get("review_count") or 0,
                    "address": venue.get("address"),
                    "phone": venue.get("phone"),
                    "website": venue.get("website"),
                    "cuisine_match_score": venue.get("cuisine_match_score", 0),
                    "matched_vibes": venue.get("matched_vibes", [])
                })
                
                used_place_ids.add(place_id)
                current_lat = venue["latitude"]
                current_lon = venue["longitude"]
                slots_used += 1
                
                # Advance time (estimate 1.5 hours per stop)
                current_hour = (current_hour + 1) % 24
                if current_hour == 0:
                    current_hour = 24
        
        return itinerary
    
    def _select_venue_for_slot(
        self,
        venues: List[Dict],
        slot_name: str,
        current_lat: float,
        current_lon: float,
        used_place_ids: set
    ) -> Optional[Dict]:
        """Select best venue for a time slot"""
        slot_categories = {
            "coffee": ["coffee", "cafe", "bakery", "breakfast"],
            "activity": ["park", "museum", "gallery", "bookstore", "shopping"],
            "brunch": ["restaurant", "brunch", "cafe"],
            "afternoon": ["park", "bookstore", "museum", "gallery"],
            "lunch": ["restaurant", "lunch", "food"],
            "dinner": ["restaurant", "dinner", "fine_dining"],
            "nightlife": ["bar", "nightclub", "lounge", "speakeasy"],
        }
        
        target_categories = slot_categories.get(slot_name, [])
        
        candidates = []
        for venue in venues:
            place_id = venue.get("place_id")
            # Skip venues without place_id or already used
            if not place_id or place_id in used_place_ids:
                continue
            
            # Check if venue matches slot category (simplified - would need category field)
            # For now, we'll use distance and rating
            try:
                dist = haversine_distance(
                    current_lat, current_lon,
                    float(venue["latitude"]), float(venue["longitude"])
                )
            except (ValueError, TypeError):
                continue  # Skip venues with invalid coordinates
            
            rating = venue.get("rating", 0) or 0
            
            # Score: higher rating, closer distance
            score = rating * 20 - (dist / 100)  # Rating weighted more
            
            # Boost hidden gems significantly to ensure at least one is included
            if venue.get("is_hidden_gem", False):
                score += 50  # Significant boost for hidden gems
            
            candidates.append((score, venue, dist))
        
        if not candidates:
            return None
        
        # Sort by score
        candidates.sort(key=lambda x: -x[0])
        
        # Filter to candidates within reasonable distance (1.5km)
        nearby_candidates = [(s, v, d) for s, v, d in candidates if d <= 1500]
        if not nearby_candidates:
            nearby_candidates = candidates[:5]  # Fall back to top 5 if none nearby
        
        # Randomly select from top candidates for variety
        # Weight selection towards higher scores but still random
        if len(nearby_candidates) > 1:
            # Select from top 3-5 candidates with weighted probability
            top_n = min(5, len(nearby_candidates))
            weights = [1.0 / (i + 1) for i in range(top_n)]  # [1.0, 0.5, 0.33, 0.25, 0.2]
            selected_idx = random.choices(range(top_n), weights=weights, k=1)[0]
            return nearby_candidates[selected_idx][1]
        
        return nearby_candidates[0][1] if nearby_candidates else None
    
    def _calculate_vibe_match(self, venue: Dict, slot_name: str) -> float:
        """Calculate how well venue matches the slot vibe"""
        # Simplified: return random score between 0.6-0.9
        # In production, would check venue_vibes table
        return round(random.uniform(0.6, 0.9), 2)
    
    def _calculate_walk_time(self, itinerary: List[Dict]) -> int:
        """Calculate total walking time between stops"""
        if len(itinerary) <= 1:
            return 0
        
        total_distance = 0
        for i in range(len(itinerary) - 1):
            total_distance += itinerary[i].get("distance_m", 0)
        
        # Walking speed: ~5 km/h = 83.3 m/min
        return int(total_distance / 83.3)
    
    def _generate_narrative(
        self,
        itinerary: List[Dict],
        selected_vibe: Optional[str],
        social_context: str
    ) -> str:
        """Generate a narrative description of the itinerary"""
        vibe_text = selected_vibe.replace("_", " ").title() if selected_vibe else "curated"
        context_text = social_context.title()
        
        stops = [item["name"] for item in itinerary[:3]]
        if len(stops) >= 3:
            return f"A {vibe_text} day for {context_text}s: {stops[0]}, {stops[1]}, and {stops[2]}..."
        elif len(stops) == 2:
            return f"A {vibe_text} day for {context_text}s: {stops[0]} and {stops[1]}"
        else:
            return f"A {vibe_text} day for {context_text}s in NYC"
    
    def get_venue_details(self, place_ids: List[str]) -> List[Dict]:
        """Fetch full details for venues by place_ids"""
        if not self.supabase:
            return []
        
        try:
            # Fetch venues
            result = self.supabase.table("venues").select("*").in_("place_id", place_ids).execute()
            venues = result.data if result.data else []
            
            # Fetch insights including full_ai_json
            insights = {}
            try:
                insights_result = self.supabase.table("place_insights").select("place_id, full_ai_json, display_hook, display_short_name, work_friendly, is_trap, safety_flag").in_("place_id", place_ids).execute()
                if insights_result.data:
                    for ins in insights_result.data:
                        place_id = ins.get("place_id")
                        if place_id:
                            insights[place_id] = ins
            except Exception as e:
                print(f"Error fetching insights batch: {e}")
                # Fallback: fetch individually if batch query fails
                for place_id in place_ids:
                    try:
                        result = self.supabase.table("place_insights").select("place_id, full_ai_json, display_hook, display_short_name, work_friendly, is_trap, safety_flag").eq("place_id", place_id).limit(1).execute()
                        if result.data:
                            insights[place_id] = result.data[0]
                    except Exception as e2:
                        print(f"Error fetching insight for {place_id}: {e2}")
                        continue
            
            # Combine data
            detailed_venues = []
            for venue in venues:
                place_id = venue["place_id"]
                insight = insights.get(place_id, {})
                
                # Parse full_ai_json if available
                rich_data = None
                if insight.get("full_ai_json"):
                    try:
                        import json
                        if isinstance(insight["full_ai_json"], str):
                            rich_data = json.loads(insight["full_ai_json"])
                        elif isinstance(insight["full_ai_json"], dict):
                            rich_data = insight["full_ai_json"]
                    except Exception as e:
                        print(f"Error parsing full_ai_json for {place_id}: {e}")
                        rich_data = None
                
                detailed_venues.append({
                    "place_id": place_id,
                    "name": venue.get("name"),
                    "address": venue.get("address"),
                    "street_address": venue.get("street_address"),
                    "city": venue.get("city"),
                    "state": venue.get("state"),
                    "zip": venue.get("zip"),
                    "latitude": venue.get("latitude"),
                    "longitude": venue.get("longitude"),
                    "rating": venue.get("rating"),
                    "review_count": venue.get("review_count"),
                    "phone": venue.get("phone"),
                    "website": venue.get("website"),
                    "hours": venue.get("hours"),
                    "photos": venue.get("photos"),
                    "opentable_url": venue.get("opentable_url"),
                    "resy_url": venue.get("resy_url"),
                    "accepts_reservations": venue.get("accepts_reservations"),
                    "insights": {
                        "display_hook": insight.get("display_hook"),
                        "display_short_name": insight.get("display_short_name"),
                        "work_friendly": insight.get("work_friendly", False),
                        "is_trap": insight.get("is_trap", False),
                        "safety_flag": insight.get("safety_flag", False),
                    } if insight else {},
                    "rich_data": rich_data  # Include full_ai_json parsed data
                })
            
            return detailed_venues
            
        except Exception as e:
            print(f"Error fetching venue details: {e}")
            return []

