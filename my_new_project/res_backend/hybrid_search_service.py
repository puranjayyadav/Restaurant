from typing import List, Dict, Any, Optional
from .embedding_service import EmbeddingService

class HybridSearchService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.supabase = self.embedding_service.supabase
    
    def search(
        self,
        query: str,
        vibe_slugs: List[str] = None,
        cuisine_slugs: List[str] = None,
        lat: float = None,
        lng: float = None,
        radius_km: float = 5.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic, vibe, and insight scoring.
        
        Args:
            query: Natural language search query
            vibe_slugs: List of vibe slugs to filter by (e.g., ['dinner_date', 'work_friendly'])
            cuisine_slugs: List of cuisine slugs to filter by (e.g., ['indian_north', 'korean_bbq'])
            lat/lng: User location for proximity filtering
            radius_km: Search radius in kilometers
            limit: Maximum number of results
        
        Returns:
            List of venues with hybrid scores
        """
        # Normalize cuisine slugs - convert generic names to actual vibe slugs
        CUISINE_EXPANSION = {
            'indian': ['indian_north', 'indian_south', 'indian_north_aesthetic', 'indian_south_aesthetic'],
            'korean': ['korean_bbq', 'korean_bbq_aesthetic', 'korean_pocha', 'korean_pocha_aesthetic'],
            'japanese': ['japanese_izakaya', 'japanese_izakaya_aesthetic', 'japanese_sushi_aesthetic'],
            'thai': ['thai_isan', 'thai_isan_aesthetic'],
            'italian': ['italian_red_sauce', 'italian_red_sauce_aesthetic'],
            'chinese': ['chinese_sichuan', 'chinese_sichuan_aesthetic', 'chinese_cantonese', 'chinese_cantonese_aesthetic'],
            'mexican': ['mexican_street', 'mexican_street_aesthetic'],
            'vietnamese': ['vietnamese_pho', 'vietnamese_pho_aesthetic'],
            'french': ['french_bistro', 'french_bistro_aesthetic'],
            'mediterranean': ['mediterranean', 'mediterranean_aesthetic'],
            'coffee': ['coffee', 'coffee_run', 'coffee_aesthetic'],
            'pizza': ['pizza_nyc', 'pizza_nyc_aesthetic'],
        }
        
        if cuisine_slugs:
            expanded_slugs = []
            for slug in cuisine_slugs:
                slug_lower = slug.lower().strip()
                if slug_lower in CUISINE_EXPANSION:
                    expanded_slugs.extend(CUISINE_EXPANSION[slug_lower])
                    print(f"DEBUG: Expanded cuisine '{slug}' to {CUISINE_EXPANSION[slug_lower]}")
                else:
                    # Keep the original slug if it's already a valid vibe slug
                    expanded_slugs.append(slug_lower)
            cuisine_slugs = list(set(expanded_slugs))  # Remove duplicates
        
        # If cuisine is specified, use fallback search directly for reliability
        # The RPC function has issues with cuisine filtering
        if cuisine_slugs and len(cuisine_slugs) > 0:
            print(f"DEBUG: Using fallback search for cuisine-specific query: {cuisine_slugs}")
            return self._fallback_search(vibe_slugs, cuisine_slugs, lat, lng, radius_km, limit)
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            if not query_embedding:
                print("Warning: Failed to generate query embedding, falling back to structured search")
                return self._fallback_search(vibe_slugs, cuisine_slugs, lat, lng, radius_km, limit)
            
            # Call hybrid search function in Supabase
            result = self.supabase.rpc('hybrid_search_venues', {
                'query_embedding': query_embedding,
                'vibe_slugs': vibe_slugs or [],
                'cuisine_slugs': cuisine_slugs or [],
                'match_threshold': 0.3,
                'lat': lat,
                'lng': lng,
                'radius_km': radius_km,
                'limit_count': limit
            }).execute()
            
            results = result.data if result.data else []
            
            # If results are empty or too few, try fallback
            if len(results) < 3:
                print(f"DEBUG: RPC returned only {len(results)} results, trying fallback")
                fallback_results = self._fallback_search(vibe_slugs, cuisine_slugs, lat, lng, radius_km, limit)
                if len(fallback_results) > len(results):
                    return fallback_results
            
            return results
            
        except Exception as e:
            print(f"Hybrid search error: {e}")
            return self._fallback_search(vibe_slugs, cuisine_slugs, lat, lng, radius_km, limit)
    
    def _fallback_search(
        self,
        vibe_slugs: List[str],
        cuisine_slugs: List[str],
        lat: float,
        lng: float,
        radius_km: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback to structured search when embeddings fail."""
        import math
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth's radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.asin(math.sqrt(a))
        
        try:
            # PRIORITY: If cuisine_slugs are provided, filter by cuisine FIRST
            # This ensures cuisine-specific queries return cuisine-specific results
            if cuisine_slugs:
                # Get venues matching cuisine
                print(f"DEBUG: Fallback searching for cuisines: {cuisine_slugs}")
                result = self.supabase.table('venue_vibes').select(
                    'place_id, vibe_slug, venues!inner(place_id, name, address, latitude, longitude, rating)'
                ).in_('vibe_slug', cuisine_slugs).limit(500).execute()
                
                # Aggregate by place_id to get all matched vibes
                venue_map = {}
                for row in result.data:
                    venue = row.get('venues', {})
                    place_id = venue.get('place_id')
                    if not place_id:
                        continue
                    
                    if place_id not in venue_map:
                        venue_map[place_id] = {
                            'place_id': place_id,
                            'name': venue.get('name'),
                            'address': venue.get('address'),
                            'latitude': venue.get('latitude'),
                            'longitude': venue.get('longitude'),
                            'rating': venue.get('rating'),
                            'matched_vibes': set()
                        }
                    venue_map[place_id]['matched_vibes'].add(row.get('vibe_slug'))
                
                print(f"DEBUG: Found {len(venue_map)} unique venues with cuisine match")
                
                # Filter by location and rating, sort by cuisine match count
                venues = []
                for place_id, venue in venue_map.items():
                    # Skip venues without coordinates
                    if not venue.get('latitude') or not venue.get('longitude'):
                        continue
                    
                    # Skip low-rated venues
                    rating = venue.get('rating') or 0
                    if rating < 4.0:
                        continue
                    
                    # Filter by distance if location provided
                    if lat and lng:
                        try:
                            dist = haversine(lat, lng, float(venue['latitude']), float(venue['longitude']))
                            if dist > radius_km:
                                continue
                            venue['distance_km'] = dist
                        except (ValueError, TypeError):
                            continue
                    
                    # Calculate cuisine match score
                    cuisine_match_count = len(venue['matched_vibes'].intersection(set(cuisine_slugs)))
                    venue['cuisine_match_score'] = cuisine_match_count
                    venue['matched_vibes'] = list(venue['matched_vibes'])
                    venue['semantic_score'] = 0.0
                    venue['vibe_match_score'] = 1.0 if cuisine_match_count > 0 else 0.0
                    venue['insight_score'] = 0.0
                    venue['final_score'] = 0.5 + (0.1 * cuisine_match_count)  # Higher score for more matches
                    
                    venues.append(venue)
                
                # Add randomization for variety while maintaining quality
                import random
                
                # Group venues by quality tier (high: 4.5+, medium: 4.0-4.5)
                high_rated = [v for v in venues if (v.get('rating') or 0) >= 4.5]
                medium_rated = [v for v in venues if 4.0 <= (v.get('rating') or 0) < 4.5]
                
                # Shuffle within each tier for variety
                random.shuffle(high_rated)
                random.shuffle(medium_rated)
                
                # Sort each tier by cuisine match score (descending) but keep randomness within same score
                high_rated.sort(key=lambda v: -v.get('cuisine_match_score', 0))
                medium_rated.sort(key=lambda v: -v.get('cuisine_match_score', 0))
                
                # Combine: prioritize high-rated, then medium-rated
                randomized_venues = high_rated + medium_rated
                
                # Return more than requested (3x) so caller can further randomize
                return_count = min(limit * 3, len(randomized_venues))
                print(f"DEBUG: Returning {return_count} cuisine-filtered venues (shuffled for variety)")
                return randomized_venues[:return_count]
            
            # If no cuisine specified, use vibe-based search
            elif vibe_slugs:
                print(f"DEBUG: Fallback searching for vibes: {vibe_slugs}")
                result = self.supabase.table('venue_vibes').select(
                    'place_id, venues!inner(place_id, name, address, latitude, longitude, rating)'
                ).in_('vibe_slug', vibe_slugs).limit(limit).execute()
                
                venues = []
                for row in result.data:
                    venue = row.get('venues', {})
                    venues.append({
                        'place_id': venue.get('place_id'),
                        'name': venue.get('name'),
                        'address': venue.get('address'),
                        'latitude': venue.get('latitude'),
                        'longitude': venue.get('longitude'),
                        'rating': venue.get('rating'),
                        'semantic_score': 0.0,
                        'vibe_match_score': 1.0,
                        'insight_score': 0.0,
                        'final_score': 0.25
                    })
                
                return venues
            
            return []
            
        except Exception as e:
            print(f"Fallback search error: {e}")
            import traceback
            traceback.print_exc()
            return []
