"""
Day Planner Service V2 - Intent-Driven Query Processing

This is a complete rewrite of the day_planner_service using modular architecture:
- IntentParser: LLM-based intent extraction
- VibeResolver: Database-driven vibe resolution
- VenueDiscovery: Multi-signal venue scoring
- ItineraryComposer: Intelligent itinerary assembly

Usage:
    service = DayPlannerServiceV2()
    
    # From natural language query
    result = service.generate_from_query("romantic indian dinner in soho")
    
    # Or with explicit parameters (backwards compatible)
    result = service.generate_itinerary(
        start_lat=40.7233,
        start_long=-74.0030,
        selected_vibe="dinner_date",
        cuisine_preferences=["indian_north"]
    )
"""
import uuid
import math
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

# Try to import supabase_config from parent directory
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from supabase_config import get_supabase_client
from .intent_parser import IntentParser, ParsedIntent
from .vibe_resolver import VibeResolver
from .venue_discovery import VenueDiscovery, ScoredVenue
from .itinerary_composer import ItineraryComposer, ItineraryStop


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in meters."""
    R = 6371000  # Earth radius in meters
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


class DayPlannerServiceV2:
    """
    Intent-Driven Day Planner Service.
    
    Processes natural language queries through a 4-stage pipeline:
    1. Intent Parsing: Extract structured intent from query
    2. Vibe Resolution: Map raw terms to actual vibe_slugs
    3. Venue Discovery: Find and score matching venues
    4. Itinerary Composition: Build diverse, walkable itinerary
    """
    
    # NYC neighborhoods for geocoding fallback
    NYC_NEIGHBORHOODS = {
        "soho": (40.7233, -74.0030),
        "nolita": (40.7234, -73.9956),
        "tribeca": (40.7163, -74.0086),
        "noho": (40.7270, -73.9927),
        "williamsburg": (40.7081, -73.9571),
        "bushwick": (40.6944, -73.9213),
        "greenpoint": (40.7282, -73.9442),
        "east village": (40.7265, -73.9815),
        "west village": (40.7358, -74.0036),
        "lower east side": (40.7150, -73.9843),
        "les": (40.7150, -73.9843),
        "upper east side": (40.7736, -73.9566),
        "ues": (40.7736, -73.9566),
        "upper west side": (40.7870, -73.9754),
        "uws": (40.7870, -73.9754),
        "chelsea": (40.7465, -74.0014),
        "flatiron": (40.7410, -73.9896),
        "gramercy": (40.7380, -73.9855),
        "midtown": (40.7549, -73.9840),
        "times square": (40.7580, -73.9855),
        "hell's kitchen": (40.7638, -73.9918),
        "harlem": (40.8116, -73.9465),
        "brooklyn heights": (40.6960, -73.9936),
        "dumbo": (40.7033, -73.9883),
        "park slope": (40.6710, -73.9814),
        "prospect heights": (40.6775, -73.9692),
        "crown heights": (40.6694, -73.9422),
        "fort greene": (40.6907, -73.9755),
        "bed stuy": (40.6872, -73.9418),
        "astoria": (40.7644, -73.9235),
        "long island city": (40.7440, -73.9419),
        "downtown": (40.7128, -74.0060),
        "uptown": (40.7900, -73.9600),
    }
    
    # Map price preferences to venue tiers
    PRICE_TO_TIER = {
        "premium": "premium",
        "upscale": "premium",
        "budget": "standard",
        "moderate": "reliable",
    }
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.intent_parser = IntentParser()
        self.vibe_resolver = VibeResolver()
        self.venue_discovery = VenueDiscovery()
        self.itinerary_composer = ItineraryComposer()
    
    def generate_from_query(
        self,
        query: str,
        start_lat: Optional[float] = None,
        start_long: Optional[float] = None,
        radius_meters: int = 1500,
        user_id: Optional[str] = None,
        exclude_place_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate an itinerary from a natural language query.
        
        This is the main entry point for natural language processing.
        
        Args:
            query: Natural language query (e.g., "romantic indian dinner in soho")
            start_lat: Optional override for latitude
            start_long: Optional override for longitude
            radius_meters: Search radius
            user_id: Optional user ID for history tracking
            
        Returns:
            Dict with itinerary, narrative, walk_time, etc.
        """
        print(f"DEBUG V2: Processing query: {query}")
        
        # Stage 1: Parse Intent
        intent = self.intent_parser.parse(query)
        print(f"DEBUG V2: Parsed intent: {intent.to_dict()}")
        
        # Stage 2: Resolve coordinates
        lat, lng = self._resolve_coordinates(
            intent.raw_location,
            start_lat,
            start_long
        )
        print(f"DEBUG V2: Resolved coordinates: ({lat}, {lng})")
        
        # Stage 3: Resolve vibes
        vibe_slugs = self.vibe_resolver.resolve_with_expansions(
            raw_cuisine=intent.raw_cuisine,
            raw_occasion=intent.raw_occasion,
            raw_requirements=intent.requirements
        )
        print(f"DEBUG V2: Resolved vibes: {vibe_slugs}")
        
        # Stage 4: Discover venues
        tier_preference = self.PRICE_TO_TIER.get(intent.price_preference)
        venues = self.venue_discovery.find_venues(
            vibe_slugs=vibe_slugs,
            lat=lat,
            lng=lng,
            radius_m=radius_meters,
            min_reviews=50,
            limit=50,
            tier_preference=tier_preference,
            requirements=intent.requirements
        )
        print(f"DEBUG V2: Found {len(venues)} venues")
        
        if not venues:
            return {"error": "No venues found matching your criteria"}
        
        # Stage 5: Compose itinerary
        target_stops = self._determine_target_stops(intent)
        itinerary_stops = self.itinerary_composer.compose(
            venues=venues,
            time_preference=intent.time_preference,
            target_stops=target_stops,
            start_lat=lat,
            start_lng=lng
        )
        print(f"DEBUG V2: Composed {len(itinerary_stops)} stops")
        
        # Calculate metrics
        total_walk_time = self.itinerary_composer.calculate_total_walk_time(itinerary_stops)
        narrative = self.itinerary_composer.generate_narrative(
            itinerary_stops,
            occasion=intent.raw_occasion
        )
        
        # Generate itinerary ID
        itinerary_id = str(uuid.uuid4())
        
        # Convert stops to dict format
        itinerary = [stop.to_dict() for stop in itinerary_stops]
        
        # Count tiers
        tier_counts = {}
        for stop in itinerary_stops:
            tier_counts[stop.venue_tier] = tier_counts.get(stop.venue_tier, 0) + 1
        
        # Stage 6: Find Spotlight Recommendation
        # A premium venue with high reviews (200-3000+) and rating 4.5+ 
        # that wasn't included in the itinerary
        excluded_for_spotlight = [stop.place_id for stop in itinerary_stops]
        if exclude_place_ids:
            excluded_for_spotlight.extend(exclude_place_ids)

        spotlight = self._find_spotlight_recommendation(
            lat=lat,
            lng=lng,
            radius_m=radius_meters,
            vibe_slugs=vibe_slugs,
            excluded_place_ids=excluded_for_spotlight
        )
        
        result = {
            "itinerary_id": itinerary_id,
            "itinerary": itinerary,
            "total_walk_time_mins": total_walk_time,
            "narrative": narrative,
            "hidden_gems_injected": tier_counts.get("hidden_gem", 0),
            "parsed_intent": intent.to_dict(),
            "resolved_vibes": vibe_slugs,
        }
        
        # Add spotlight if found
        if spotlight:
            result["spotlight_recommendation"] = spotlight
            print(f"DEBUG V2: Found spotlight: {spotlight.get('name')} ({spotlight.get('rating')}⭐, {spotlight.get('review_count')} reviews)")
        
        return result
    
    def generate_itinerary(
        self,
        start_lat: Optional[float] = None,
        start_long: Optional[float] = None,
        selected_vibe: Optional[str] = None,
        social_context: str = "couple",
        radius_meters: int = 1500,
        local_time_start: str = "10:00",
        cuisine_preferences: Optional[List[str]] = None,
        cuisine_preference_min: Optional[int] = None,
        cuisine_preference_max: Optional[int] = None,
        user_id: Optional[str] = None,
        exclude_place_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate an itinerary with explicit parameters (backwards compatible).
        
        This maintains compatibility with the existing API contract.
        """
        print(f"DEBUG V2: generate_itinerary called with explicit params")
        print(f"DEBUG V2: vibe={selected_vibe}, cuisine={cuisine_preferences}, location=({start_lat}, {start_long})")
        
        # If no coordinates, use a random NYC location
        if start_lat is None or start_long is None:
            import random
            neighborhood = random.choice(list(self.NYC_NEIGHBORHOODS.keys()))
            start_lat, start_long = self.NYC_NEIGHBORHOODS[neighborhood]
            print(f"DEBUG V2: Using random neighborhood: {neighborhood}")
        
        # Resolve time preference from local_time_start
        try:
            hour = int(local_time_start.split(":")[0])
            if hour < 11:
                time_preference = "morning"
            elif hour < 17:
                time_preference = "afternoon"
            elif hour < 21:
                time_preference = "evening"
            else:
                time_preference = "late_night"
        except:
            time_preference = "evening"
        
        # Build vibe list from parameters
        vibe_slugs = []
        
        # Add selected vibe
        if selected_vibe:
            # Map common vibe names
            vibe_mapping = {
                "romantic": "dinner_date",
                "romance": "dinner_date",
            }
            mapped_vibe = vibe_mapping.get(selected_vibe, selected_vibe)
            resolved = self.vibe_resolver.resolve(raw_occasion=mapped_vibe)
            vibe_slugs.extend(resolved)
        
        # Add cuisine preferences
        if cuisine_preferences:
            for cuisine in cuisine_preferences:
                resolved = self.vibe_resolver.resolve(raw_cuisine=cuisine)
                vibe_slugs.extend(resolved)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_vibes = []
        for v in vibe_slugs:
            if v not in seen:
                seen.add(v)
                unique_vibes.append(v)
        vibe_slugs = unique_vibes
        
        print(f"DEBUG V2: Resolved vibe_slugs: {vibe_slugs}")
        
        # Discover venues
        venues = self.venue_discovery.find_venues(
            vibe_slugs=vibe_slugs,
            lat=start_lat,
            lng=start_long,
            radius_m=radius_meters,
            min_reviews=50,
            limit=50
        )
        print(f"DEBUG V2: Found {len(venues)} venues")
        
        if not venues:
            return {"error": "No venues found in the specified area"}
        
        # Determine target stops based on social context
        target_stops_map = {
            "couple": 4,
            "solo": 3,
            "group": 5,
            "family": 4,
        }
        target_stops = target_stops_map.get(social_context, 4)
        
        # Compose itinerary
        itinerary_stops = self.itinerary_composer.compose(
            venues=venues,
            time_preference=time_preference,
            target_stops=target_stops,
            start_lat=start_lat,
            start_lng=start_long
        )
        print(f"DEBUG V2: Composed {len(itinerary_stops)} stops")
        
        # Calculate metrics
        total_walk_time = self.itinerary_composer.calculate_total_walk_time(itinerary_stops)
        narrative = self.itinerary_composer.generate_narrative(
            itinerary_stops,
            occasion=selected_vibe
        )
        
        # Generate itinerary ID
        itinerary_id = str(uuid.uuid4())
        
        # Convert stops to dict format (matching original API structure)
        itinerary = []
        for stop in itinerary_stops:
            itinerary.append({
                "slot": stop.slot,
                "time": stop.time,
                "place_id": stop.place_id,
                "name": stop.name,
                "latitude": stop.latitude,
                "longitude": stop.longitude,
                "rating": stop.rating,
                "review_count": stop.review_count,
                "address": stop.address,
                "distance_m": stop.distance_m,
                "vibe_match": stop.vibe_match,
                "is_hidden_gem": stop.venue_tier == "hidden_gem",
                "matched_vibes": stop.matched_vibes,
            })
        
        # Count hidden gems
        hidden_gems_count = sum(1 for s in itinerary_stops if s.venue_tier == "hidden_gem")
        
        # Find Spotlight Recommendation
        excluded_for_spotlight = [stop.place_id for stop in itinerary_stops]
        if exclude_place_ids:
            excluded_for_spotlight.extend(exclude_place_ids)

        spotlight = self._find_spotlight_recommendation(
            lat=start_lat,
            lng=start_long,
            radius_m=radius_meters,
            vibe_slugs=vibe_slugs,
            excluded_place_ids=excluded_for_spotlight
        )
        
        result = {
            "itinerary_id": itinerary_id,
            "itinerary": itinerary,
            "hidden_gems_injected": hidden_gems_count,
            "total_walk_time_mins": total_walk_time,
            "narrative": narrative,
        }
        
        # Add spotlight if found
        if spotlight:
            result["spotlight_recommendation"] = spotlight
        
        return result
    
    def _resolve_coordinates(
        self,
        location_hint: Optional[str],
        override_lat: Optional[float],
        override_lng: Optional[float]
    ) -> Tuple[float, float]:
        """Resolve coordinates from location hint or overrides."""
        # Use overrides if provided
        if override_lat is not None and override_lng is not None:
            return override_lat, override_lng
        
        # Try to resolve from location hint
        if location_hint:
            hint_lower = location_hint.lower().strip()
            
            # Direct neighborhood match
            if hint_lower in self.NYC_NEIGHBORHOODS:
                return self.NYC_NEIGHBORHOODS[hint_lower]
            
            # Partial match
            for neighborhood, coords in self.NYC_NEIGHBORHOODS.items():
                if hint_lower in neighborhood or neighborhood in hint_lower:
                    return coords
        
        # Default to SoHo (central Manhattan)
        return self.NYC_NEIGHBORHOODS["soho"]
    
    def _determine_target_stops(self, intent: ParsedIntent) -> int:
        """Determine target number of stops based on intent."""
        # Base on party size
        if intent.party_size:
            if intent.party_size >= 6:
                return 5
            elif intent.party_size >= 4:
                return 4
            elif intent.party_size == 1:
                return 3
        
        # Base on time preference
        if intent.time_preference == "morning":
            return 3  # Shorter morning itineraries
        elif intent.time_preference == "late_night":
            return 3  # Fewer late-night options
        
        return 4  # Default
    
    def _find_spotlight_recommendation(
        self,
        lat: float,
        lng: float,
        radius_m: int,
        vibe_slugs: List[str],
        excluded_place_ids: List[str]
    ) -> Optional[Dict]:
        """
        Find a premium "spotlight" recommendation - a highly-rated, popular venue
        that wasn't included in the itinerary.
        
        Criteria:
        - Rating >= 4.5
        - Review count between 200 and 5000 (popular but not a tourist trap)
        - Not in the current itinerary
        - Matches at least one of the vibe slugs (optional bonus)
        - Business status is OPEN or NULL
        
        Returns:
            Dict with venue details and a special message, or None if not found
        """
        if not self.supabase:
            return None
        
        try:
            # Query venues table for premium spots
            # Use a wider radius to find great spots nearby (1.5x the itinerary radius)
            base_radius_km = max(3.0, (radius_m or 0) / 1000.0 * 1.5)
            radius_steps = [
                base_radius_km,
                max(5.0, base_radius_km * 2.0),
                max(8.0, base_radius_km * 3.0),
            ]
            excluded_set = {pid for pid in excluded_place_ids if pid}
            
            candidates = []
            for search_radius_km in radius_steps:
                # Calculate bounding box
                lat_delta = search_radius_km / 111  # ~111km per degree latitude
                lng_delta = search_radius_km / (111 * math.cos(math.radians(lat)))
                
                min_lat = lat - lat_delta
                max_lat = lat + lat_delta
                min_lng = lng - lng_delta
                max_lng = lng + lng_delta
                
                # Query for premium venues
                result = self.supabase.table("venues").select(
                    "place_id, name, address, latitude, longitude, rating, review_count, "
                    "price_range, photos, business_status"
                ).gte("rating", 4.5).gte("review_count", 100).lte("review_count", 15000).gte(
                    "latitude", min_lat
                ).lte("latitude", max_lat).gte(
                    "longitude", min_lng
                ).lte("longitude", max_lng).order(
                    "review_count", desc=True
                ).limit(30).execute()
                
                if result.data:
                    candidates = result.data
                    break
            
            if not candidates:
                return None
            
            # Filter out venues already in itinerary and closed businesses
            candidates = [
                v for v in candidates
                if v.get("place_id") not in excluded_set
                and v.get("business_status") in (None, "OPERATIONAL", "OPEN", "")
            ]
            
            if not candidates:
                return None
            
            # Prefer venues that match the vibes, but allow variety via weighted sampling.
            scored_candidates = []

            for venue in candidates:
                score = 0.0

                # Score by rating (max 10 points)
                rating = venue.get("rating", 0) or 0
                score += (rating - 4.0) * 10  # 4.5 = 5 points, 5.0 = 10 points

                # Score by review count (max 10 points, log scale)
                review_count = venue.get("review_count", 0) or 0
                if review_count >= 1000:
                    score += 10
                elif review_count >= 500:
                    score += 7
                elif review_count >= 300:
                    score += 5
                else:
                    score += 3

                # Distance penalty (avoid always picking farthest)
                try:
                    distance_m = haversine_distance(
                        lat, lng, venue.get("latitude"), venue.get("longitude")
                    )
                    score -= min(5.0, distance_m / 1000.0)
                except Exception:
                    pass

                # Check for vibe match via venue_vibes table (bonus 5 points)
                try:
                    vibe_check = self.supabase.table("venue_vibes").select(
                        "vibe_slug"
                    ).eq("place_id", venue.get("place_id")).in_(
                        "vibe_slug", vibe_slugs
                    ).limit(1).execute()

                    if vibe_check.data:
                        score += 5
                except Exception:
                    pass

                scored_candidates.append((score, venue))

            scored_candidates.sort(key=lambda item: item[0], reverse=True)
            top_candidates = scored_candidates[: min(8, len(scored_candidates))]
            if not top_candidates:
                best_match = candidates[0]
            else:
                # Weighted choice among top candidates for variety.
                import random

                weights = [max(0.1, score) for score, _ in top_candidates]
                best_match = random.choices(
                    [venue for _, venue in top_candidates], weights=weights, k=1
                )[0]
            
            # Fetch insight for display hook if available
            display_hook = None
            try:
                insight_result = self.supabase.table("place_insights").select(
                    "display_hook, display_short_name"
                ).eq("place_id", best_match["place_id"]).limit(1).execute()
                
                if insight_result.data:
                    display_hook = insight_result.data[0].get("display_hook")
            except:
                pass
            
            # Calculate distance from center
            distance_m = haversine_distance(
                lat, lng, 
                best_match.get("latitude"), 
                best_match.get("longitude")
            )
            
            # Build the spotlight recommendation
            spotlight = {
                "place_id": best_match.get("place_id"),
                "name": best_match.get("name"),
                "address": best_match.get("address"),
                "latitude": best_match.get("latitude"),
                "longitude": best_match.get("longitude"),
                "rating": best_match.get("rating"),
                "review_count": best_match.get("review_count"),
                "price_range": best_match.get("price_range"),
                "distance_m": int(distance_m),
                "photos": (best_match.get("photos") or [])[:1],  # Just first photo
                "display_hook": display_hook,
                "spotlight_reason": self._generate_spotlight_reason(best_match),
            }
            
            return spotlight
            
        except Exception as e:
            print(f"Error finding spotlight recommendation: {e}")
            return None
    
    def _generate_spotlight_reason(self, venue: Dict) -> str:
        """Generate a compelling reason why this venue is spotlighted."""
        rating = venue.get("rating", 0) or 0
        review_count = venue.get("review_count", 0) or 0
        name = venue.get("name", "This spot")
        
        if rating >= 4.8 and review_count >= 500:
            return f"⭐ {name} is a local favorite with {review_count:,} glowing reviews!"
        elif rating >= 4.7 and review_count >= 1000:
            return f"🔥 {name} is wildly popular - {review_count:,} people can't be wrong!"
        elif rating >= 4.5 and review_count >= 500:
            return f"💎 Don't sleep on {name} - it's a neighborhood gem with {review_count:,} fans."
        elif review_count >= 1000:
            return f"📍 {name} is a must-visit with over {review_count:,} reviews."
        else:
            return f"✨ Save {name} for your next visit - locals love it!"
    
    def get_venue_details(self, place_ids: List[str]) -> List[Dict]:
        """Fetch full details for venues by place_ids."""
        if not self.supabase or not place_ids:
            return []
        
        try:
            # Fetch venues
            result = self.supabase.table("venues").select("*").in_("place_id", place_ids).execute()
            venues = result.data if result.data else []
            
            # Fetch insights
            insights = {}
            try:
                insights_result = self.supabase.table("place_insights").select(
                    "place_id, full_ai_json, display_hook, display_short_name, work_friendly, is_trap, safety_flag"
                ).in_("place_id", place_ids).execute()
                
                if insights_result.data:
                    for ins in insights_result.data:
                        place_id = ins.get("place_id")
                        if place_id:
                            insights[place_id] = ins
            except Exception as e:
                print(f"Error fetching insights: {e}")
            
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
                    except Exception:
                        pass
                
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
                    "rich_data": rich_data,
                })
            
            return detailed_venues
            
        except Exception as e:
            print(f"Error fetching venue details: {e}")
            return []
