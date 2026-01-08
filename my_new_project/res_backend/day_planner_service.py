"""
Day Planner Service - Centralized API for generating full-day itineraries
"""
import math
import random
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from supabase_config import get_supabase_client
from .utils import haversine_distance


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
    
    # NYC default center
    NYC_CENTER = (40.7128, -74.0060)
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def generate_itinerary(
        self,
        start_lat: float,
        start_long: float,
        selected_vibe: Optional[str] = None,
        social_context: str = "couple",
        radius_meters: int = 3000,
        local_time_start: str = "10:00",
        cuisine_preferences: Optional[List[str]] = None,
        cuisine_preference_min: Optional[int] = None,
        cuisine_preference_max: Optional[int] = None
    ) -> Dict:
        """
        Generate a full-day itinerary
        
        Args:
            start_lat: Starting latitude
            start_long: Starting longitude
            selected_vibe: Optional vibe slug to filter by
            social_context: couple, solo, group, or family
            radius_meters: Search radius in meters
            local_time_start: Start time in HH:MM format
        
        Returns:
            Dict with itinerary, hidden_gems_injected, total_walk_time_mins, narrative
        """
        if not self.supabase:
            return {"error": "Supabase client not available"}
        
        # Parse start time
        try:
            hour, minute = map(int, local_time_start.split(":"))
            start_hour = hour
        except:
            start_hour = 10
        
        # Use NYC center if coordinates not provided
        if not start_lat or not start_long:
            start_lat, start_long = self.NYC_CENTER
        
        # Target 7 places total
        target_stops = 7
        
        # Map "romantic" to "dinner_date" if it's not a valid vibe_slug
        vibe_mapping = {
            "romantic": "dinner_date",
            "romance": "dinner_date",
        }
        final_vibe = vibe_mapping.get(selected_vibe, selected_vibe) if selected_vibe else None
        
        # Fetch filtered venues (with vibe/cuisine preferences) - limit to max 3
        filtered_venues = self._fetch_venues(
            start_lat, start_long, radius_meters, final_vibe,
            cuisine_preferences=cuisine_preferences,
            cuisine_preference_min=cuisine_preference_min,
            cuisine_preference_max=cuisine_preference_max
        )
        
        # Inject hidden gems (1-2 entries) that match filters
        hidden_gems = self._fetch_hidden_gems(
            start_lat, start_long, radius_meters, final_vibe,
            cuisine_preferences=cuisine_preferences
        )
        gems_injected = min(2, len(hidden_gems))
        
        # Limit filtered venues to max 3 (including hidden gems)
        filtered_venues_limited = (filtered_venues + hidden_gems[:gems_injected])[:3]
        
        # Fetch diverse venues for remaining slots (coffee, parks, bookstores, other restaurants)
        diverse_venues = self._fetch_diverse_venues(
            start_lat, start_long, radius_meters,
            exclude_place_ids=[v.get("place_id") for v in filtered_venues_limited if v.get("place_id")]
        )
        
        # Combine: max 3 filtered venues + diverse venues to reach 7 total
        all_venues = filtered_venues_limited + diverse_venues
        
        if not all_venues:
            return {"error": "No venues found in the specified area"}
        
        # Build itinerary using time slots (7 places total)
        itinerary = self._build_itinerary(all_venues, start_lat, start_long, start_hour, target_stops)
        
        # Calculate total walk time
        total_walk_time = self._calculate_walk_time(itinerary)
        
        # Generate narrative
        narrative = self._generate_narrative(itinerary, selected_vibe, social_context)
        
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
        cuisine_preference_max: Optional[int] = None
    ) -> List[Dict]:
        """Fetch venues from venues table, optionally filtered by vibe"""
        try:
            # Build place_ids list from vibe and/or cuisine preferences
            place_ids = None
            vibe_place_ids = set()
            cuisine_place_ids = set()
            
            # If vibe is specified, get place_ids from venue_vibes
            if vibe_slug:
                vibe_query = self.supabase.table("venue_vibes").select("place_id").eq("vibe_slug", vibe_slug).limit(1000)
                vibe_result = vibe_query.execute()
                
                if vibe_result.data:
                    vibe_place_ids = {v["place_id"] for v in vibe_result.data if v.get("place_id")}
                    print(f"DEBUG: Found {len(vibe_place_ids)} venues with vibe {vibe_slug}")
            
            # If cuisine preferences are specified, get place_ids for those vibes
            if cuisine_preferences:
                print(f"DEBUG: Filtering by cuisine preferences: {cuisine_preferences}")
                for cuisine_vibe in cuisine_preferences:
                    try:
                        cuisine_query = self.supabase.table("venue_vibes").select("place_id").eq("vibe_slug", cuisine_vibe).limit(500)
                        cuisine_result = cuisine_query.execute()
                        if cuisine_result.data:
                            for v in cuisine_result.data:
                                if v.get("place_id"):
                                    cuisine_place_ids.add(v["place_id"])
                            print(f"DEBUG: Found {len(cuisine_result.data)} venues with cuisine vibe {cuisine_vibe}")
                    except Exception as e:
                        print(f"Error fetching cuisine {cuisine_vibe}: {e}")
                        continue
                
                print(f"DEBUG: Total cuisine place_ids: {len(cuisine_place_ids)}")
            
            # Determine final place_ids set
            if vibe_place_ids and cuisine_place_ids:
                # Try intersection first (venues with both vibe AND cuisine)
                intersection = vibe_place_ids.intersection(cuisine_place_ids)
                print(f"DEBUG: Intersection of vibe ({len(vibe_place_ids)}) and cuisine ({len(cuisine_place_ids)}): {len(intersection)} venues")
                
                if len(intersection) >= 10:  # If we have enough venues with both, use intersection
                    place_ids = list(intersection)
                    print(f"DEBUG: Using intersection (venues with both vibe and cuisine)")
                else:
                    # Not enough venues with both - use cuisine as priority, but include vibe venues as fallback
                    # Union: prioritize cuisine matches, but include vibe matches too
                    place_ids = list(cuisine_place_ids.union(vibe_place_ids))
                    print(f"DEBUG: Using union (cuisine + vibe) - {len(place_ids)} venues. Will score by cuisine match.")
            elif vibe_place_ids:
                place_ids = list(vibe_place_ids)
                print(f"DEBUG: Using vibe filter only: {len(place_ids)} venues")
            elif cuisine_place_ids:
                place_ids = list(cuisine_place_ids)
                print(f"DEBUG: Using cuisine filter only: {len(place_ids)} venues")
            else:
                # No filters - fetch all venues (will be filtered by distance/quality)
                place_ids = None
                print(f"DEBUG: No vibe or cuisine filters - fetching all venues")
            
            # Fetch venues - use PostGIS spatial query if available, otherwise fetch and filter
            # For now, fetch a reasonable set and filter in Python
            if place_ids:
                # Fetch venues matching the vibe
                venues = []
                # Process in batches to avoid query size limits
                batch_size = 100
                for i in range(0, min(len(place_ids), 500), batch_size):
                    batch_ids = place_ids[i:i+batch_size]
                    try:
                        # Use .in_() method - if it doesn't work, we'll filter manually
                        result = self.supabase.table("venues").select("*").in_("place_id", batch_ids).execute()
                        if result.data:
                            venues.extend(result.data)
                    except:
                        # Fallback: fetch all and filter
                        result = self.supabase.table("venues").select("*").limit(1000).execute()
                        if result.data:
                            venues.extend([v for v in result.data if v.get("place_id") in batch_ids])
            else:
                # No vibe filter - fetch all venues
                result = self.supabase.table("venues").select("*").limit(1000).execute()
                venues = result.data if result.data else []
            
            # Filter by distance and quality
            filtered_venues = []
            excluded_keywords = [
                'grocery', 'market', 'lumber', 'hardware', 'pharmacy', 'drug store',
                'gas station', 'convenience', 'dollar store', 'supermarket', 'warehouse',
                'wholesale', 'auto', 'car wash', 'mechanic', 'repair', 'tire',
                'bank', 'atm', 'credit union', 'insurance', 'real estate', 'lawyer',
                'dentist', 'doctor', 'clinic', 'hospital', 'veterinary', 'vet',
                'post office', 'ups store', 'fedex', 'shipping', 'dry cleaner',
                'laundromat', 'storage', 'moving', 'furniture store', 'home depot',
                'lowes', 'target', 'walmart', 'costco', 'sam\'s club'
            ]
            
            for venue in venues:
                if venue.get("latitude") and venue.get("longitude"):
                    try:
                        # Quality filters
                        name_lower = (venue.get("name") or "").lower()
                        
                        # Exclude non-restaurant venues
                        if any(keyword in name_lower for keyword in excluded_keywords):
                            continue
                        
                        # Minimum rating filter (4.0+ for quality)
                        rating = venue.get("rating") or 0
                        if rating < 4.0:
                            continue
                        
                        dist = haversine_distance(lat, lon, float(venue["latitude"]), float(venue["longitude"]))
                        if dist <= radius_meters:
                            venue["distance_m"] = dist
                            filtered_venues.append(venue)
                    except (ValueError, TypeError):
                        continue  # Skip venues with invalid coordinates
            
            # Score venues based on cuisine preference matches
            if cuisine_preferences and filtered_venues:
                cuisine_set = set(cuisine_preferences)
                venue_place_ids = [v.get("place_id") for v in filtered_venues if v.get("place_id")]
                
                # Initialize scores
                for venue in filtered_venues:
                    venue['cuisine_match_score'] = 0
                    venue['has_cuisine_match'] = False
                
                # Re-fetch venue_vibes for filtered venues to check cuisine matches
                if venue_place_ids:
                    try:
                        # Process in batches
                        batch_size = 200
                        venue_vibes_map = {}
                        for i in range(0, len(venue_place_ids), batch_size):
                            batch_ids = venue_place_ids[i:i+batch_size]
                            venue_vibes_result = self.supabase.table("venue_vibes").select("place_id, vibe_slug").in_("place_id", batch_ids).execute()
                            if venue_vibes_result.data:
                                for vv in venue_vibes_result.data:
                                    place_id = vv.get("place_id")
                                    vibe_slug = vv.get("vibe_slug")
                                    if place_id:
                                        if place_id not in venue_vibes_map:
                                            venue_vibes_map[place_id] = []
                                        venue_vibes_map[place_id].append(vibe_slug)
                        
                        # Score venues based on cuisine matches
                        for venue in filtered_venues:
                            place_id = venue.get("place_id")
                            venue_vibes = venue_vibes_map.get(place_id, [])
                            matches = cuisine_set.intersection(set(venue_vibes))
                            venue['cuisine_match_score'] = len(matches)
                            venue['has_cuisine_match'] = len(matches) > 0
                            venue['cuisine_matches'] = list(matches)
                            
                    except Exception as e:
                        print(f"Error fetching venue vibes for cuisine matching: {e}")
            
            # Sort by cuisine match (prioritize venues with cuisine matches), then rating, then distance
            filtered_venues.sort(key=lambda v: (
                -(1 if v.get("has_cuisine_match", False) else 0),  # Cuisine matches first
                -(v.get("cuisine_match_score", 0)),  # More cuisine matches better
                -(v.get("rating") or 0),  # Higher rating first
                v.get("distance_m", 999999)  # Closer first
            ))
            
            # Filter by cuisine preference min/max if specified (but don't exclude all if no matches)
            if cuisine_preferences and cuisine_preference_min is not None and len(filtered_venues) > 0:
                # Only apply min filter if we have enough venues that match
                matching_venues = [v for v in filtered_venues if v.get("cuisine_match_score", 0) >= cuisine_preference_min]
                if len(matching_venues) >= 3:  # If we have at least 3 matching venues, use them
                    filtered_venues = matching_venues
                # Otherwise, keep all venues but prioritize matches (already sorted above)
            
            if cuisine_preferences and cuisine_preference_max is not None:
                # Keep venues with at most max cuisine matches
                filtered_venues = [v for v in filtered_venues if v.get("cuisine_match_score", 0) <= cuisine_preference_max]
            
            return filtered_venues[:100]  # Return top 100 for selection
            
        except Exception as e:
            print(f"Error fetching venues: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_hidden_gems(
        self,
        lat: float,
        lon: float,
        radius_meters: int,
        vibe_slug: Optional[str] = None,
        cuisine_preferences: Optional[List[str]] = None
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
            excluded_keywords = [
                'grocery', 'market', 'lumber', 'hardware', 'pharmacy', 'drug store',
                'gas station', 'convenience', 'dollar store', 'supermarket', 'warehouse'
            ]
            
            filtered_gems = []
            for gem in gems:
                if gem.get("latitude") and gem.get("longitude"):
                    try:
                        # Quality filters
                        name_lower = (gem.get("name") or "").lower()
                        if any(keyword in name_lower for keyword in excluded_keywords):
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
            excluded_keywords = [
                'grocery', 'market', 'lumber', 'hardware', 'pharmacy', 'drug store',
                'gas station', 'convenience', 'dollar store', 'supermarket', 'warehouse'
            ]
            
            for venue in venues:
                if venue.get("latitude") and venue.get("longitude"):
                    try:
                        place_id = venue.get("place_id")
                        if place_id in exclude_set:
                            continue
                        
                        name_lower = (venue.get("name") or "").lower()
                        if any(keyword in name_lower for keyword in excluded_keywords):
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
            
            # Sort by rating and distance
            filtered_venues.sort(key=lambda v: (
                -(v.get("rating") or 0),
                v.get("distance_m", 999999)
            ))
            
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
                    "place_id": venue["place_id"],
                    "name": venue.get("name", "Unknown"),
                    "vibe_match": vibe_match,
                    "distance_m": int(dist),
                    "is_hidden_gem": venue.get("is_hidden_gem", False)
                })
                
                used_place_ids.add(venue["place_id"])
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
            if venue["place_id"] in used_place_ids:
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
            
            candidates.append((score, venue, dist))
        
        if not candidates:
            return None
        
        # Sort by score
        candidates.sort(key=lambda x: -x[0])
        
        # Return top candidate within reasonable distance (1km)
        for score, venue, dist in candidates:
            if dist <= 1000:
                return venue
        
        # If none within 1km, return top candidate anyway
        return candidates[0][1] if candidates else None
    
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
            
            # Fetch insights
            insights = {}
            try:
                insights_result = self.supabase.table("place_insights").select("*").in_("place_id", place_ids).execute()
                if insights_result.data:
                    insights = {ins["place_id"]: ins for ins in insights_result.data}
            except:
                # Fallback: fetch individually if batch query fails
                for place_id in place_ids:
                    try:
                        result = self.supabase.table("place_insights").select("*").eq("place_id", place_id).limit(1).execute()
                        if result.data:
                            insights[place_id] = result.data[0]
                    except:
                        continue
            
            # Combine data
            detailed_venues = []
            for venue in venues:
                place_id = venue["place_id"]
                insight = insights.get(place_id, {})
                
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
                    } if insight else {}
                })
            
            return detailed_venues
            
        except Exception as e:
            print(f"Error fetching venue details: {e}")
            return []

