import json
import re
import math
import random
from typing import List, Dict, Optional, Tuple

try:
    from .image_service import image_service
except ImportError:
    image_service = None  # Fallback if service is unavailable

class ItineraryEngine:
    """
    Intelligent engine that converts raw density clusters and curated data
    into structured, walkable 3-stop itineraries.
    """
    def __init__(self, db_rows: List[Dict], selected_vibe: str = "Trendy"):
        self.db_rows = db_rows
        self.selected_vibe = selected_vibe  # Store for image service

    def generate_plan(self, user_lat: float, user_lng: float, selected_vibe: str = "Trendy") -> Dict:
        """
        Generates a 3-stop itinerary based on the user's location and vibe.
        """
        # 1. FIND & CLEAN CANDIDATES
        candidates = []
        for row in self.db_rows:
            # Parse the enriched JSON string (from lemon8_articles or similar)
            try:
                if not isinstance(row, dict):
                    continue
                    
                # Handle cases where input might be already dict or string
                itinerary_data = row.get('enriched_itinerary_data')
                if isinstance(itinerary_data, str):
                    data = json.loads(itinerary_data)
                else:
                    data = itinerary_data
                
                if not data: continue
                
                # Robustly extract stops - handle both dict-wrapped and direct lists
                if isinstance(data, list):
                    stops = data
                elif isinstance(data, dict):
                    stops = data.get('stops', [])
                else:
                    stops = []
                    
                for stop in stops:
                    # DATA CLEANING: Extract Real Name from Notes
                    # Format: "Salswee - Luxury French-Asian..."
                    real_name = stop.get('place_name', 'Unknown')
                    notes = stop.get('notes', '') or stop.get('description', '')
                    
                    if " - " in notes:
                        potential_name = notes.split(' - ')[0]
                        if len(potential_name) < 40: # Length sanity check
                            real_name = potential_name

                    # Use lat/lng or latitude/longitude
                    lat = stop.get('lat') or stop.get('latitude')
                    lng = stop.get('lng') or stop.get('longitude')
                    
                    if lat is None or lng is None:
                        continue

                    # Calculate distance to tap (Haversine)
                    dist = self._get_distance(user_lat, user_lng, float(lat), float(lng))
                    
                    # Look within 3km for more variety (was 1.5km)
                    if dist < 3.0:
                        # DE-DUPLICATION: Don't add if we already have this spot in the pool
                        if any(c['name'].lower() == real_name.lower() for c in candidates):
                            continue
                            
                        solver_data = stop.get('solver_data', {}) or {}
                        candidates.append({
                            "name": real_name,
                            "lat": float(lat),
                            "lng": float(lng),
                            "category": solver_data.get('category_normalized', 'General'),
                            "time_bias": solver_data.get('time_bias', 'Anytime'),
                            "vibes": solver_data.get('vibe_tags', []) + (stop.get('vibe_tags', []) or []),
                            "description": notes,
                            "price": solver_data.get('price_tier', '$$'),
                            "rating": stop.get('rating', 4.5)
                        })
            except Exception as e:
                print(f"Error parsing stop in engine: {e}")
                continue

        # 2. STRICT VIBE PRE-FILTER
        vibe_lower = selected_vibe.lower()
        
        # Geo-seed RNG for consistent but location-varied results
        import hashlib
        seed = int(hashlib.md5(f"{user_lat:.4f}{user_lng:.4f}".encode()).hexdigest(), 16) % (10**9)
        random.seed(seed)
        
        # Filter candidates by vibe BEFORE scoring
        filtered_candidates = []
        for venue in candidates:
            venue_vibe = self._category_to_vibe(venue['category'])
            # Also check explicit vibe tags
            if venue_vibe == vibe_lower or vibe_lower in [v.lower() for v in venue['vibes']]:
                filtered_candidates.append(venue)
        
        print(f"[ItineraryEngine] Vibe Filter: {len(candidates)} candidates → {len(filtered_candidates)} after '{vibe_lower}' filter")
        
        # Fallback: If too few results, expand to all but penalize non-matches
        if len(filtered_candidates) < 3:
            print(f"[ItineraryEngine] Pool too small, using full candidates with penalty")
            filtered_candidates = candidates  # Use all, but non-matches get lower scores
        
        # 3. SCORE CANDIDATES (The "Gravity" Logic)
        scored_venues = []
        for venue in filtered_candidates:
            score = 0
            
            # Strong Vibe Match bonus
            venue_vibe = self._category_to_vibe(venue['category'])
            if venue_vibe == vibe_lower or vibe_lower in [v.lower() for v in venue['vibes']]:
                score += 50  # Increased from 40
            else:
                score -= 30  # Penalty for non-matching vibes
            
            # Proximity Weighting (Crucial for Diversity)
            dist_to_tap = self._get_distance(user_lat, user_lng, venue['lat'], venue['lng'])
            proximity_bonus = max(0, 20 * (1.0 - (dist_to_tap / 1.5))) 
            score += proximity_bonus

            # Data Richness
            if venue['time_bias'] != "Anytime":
                score += 5
            
            # Small Random Jitter (geo-seeded for variety)
            score += random.uniform(0, 10)

            # Category variety bonus
            if venue['category'] in ['Cafe', 'Restaurant', 'Bar', 'Sight']:
                score += 5
                
            scored_venues.append((score, venue))

        # Sort by score descending
        scored_venues.sort(key=lambda x: x[0], reverse=True)
        
        if not scored_venues:
            return {"error": f"No '{selected_vibe}' spots found right here. Try zooming out or moving the map slightly!"}

        # 4. BUILD THE ARCH (Anchor + Supports)
        # Pick anchor from top 5 using weighted random for variety
        top_candidates = scored_venues[:min(5, len(scored_venues))]
        weights = [max(1, score) for score, _ in top_candidates]  # Use scores as weights
        anchor = random.choices([v for _, v in top_candidates], weights=weights, k=1)[0]
        
        print(f"[ItineraryEngine] Selected anchor '{anchor['name']}' from {len(scored_venues)} candidates")
        
        plan = []
        used_images = []
        
        # LOGIC: Build timeline based on Anchor's time bias
        if anchor['time_bias'] == 'Morning':
            s1 = self._create_stop(anchor, "Start your day here", "09:00 AM", used_images)
            plan.append(s1)
            used_images.append(s1['postgres_data']['photos'][0])
            
            lunch = self._find_complement(scored_venues, ["Restaurant", "Brunch"], exclude_names=[anchor['name']], anchor=anchor)
            if lunch: 
                s2 = self._create_stop(lunch, "Grab lunch nearby", "12:00 PM", used_images)
                plan.append(s2)
                used_images.append(s2['postgres_data']['photos'][0])
                
                park = self._find_complement(scored_venues, ["Sight", "Park", "General"], exclude_names=[anchor['name'], lunch['name']], anchor=anchor)
                if park: 
                    s3 = self._create_stop(park, "Post-meal stroll", "02:00 PM", used_images)
                    plan.append(s3)
                    used_images.append(s3['postgres_data']['photos'][0])
            
        elif anchor['time_bias'] == 'Evening':
            pre = self._find_complement(scored_venues, ["Bar", "Sight", "General"], exclude_names=[anchor['name']], anchor=anchor)
            if pre: 
                s1 = self._create_stop(pre, "Sunset drinks & views", "06:00 PM", used_images)
                plan.append(s1)
                used_images.append(s1['postgres_data']['photos'][0])
                
            s2 = self._create_stop(anchor, "Dinner highlight", "07:30 PM", used_images)
            plan.append(s2)
            used_images.append(s2['postgres_data']['photos'][0])
            
            night = self._find_complement(scored_venues, ["Bar", "Dessert"], exclude_names=[anchor['name'], (pre['name'] if pre else "")], anchor=anchor)
            if night: 
                s3 = self._create_stop(night, "Late night vibes", "09:30 PM", used_images)
                plan.append(s3)
                used_images.append(s3['postgres_data']['photos'][0])
            
        else:
            # Default "Power 3" (Anchor + 2 neighbors)
            s1 = self._create_stop(anchor, "The Main Event", "02:00 PM", used_images)
            plan.append(s1)
            used_images.append(s1['postgres_data']['photos'][0])
            
            s2_venue = self._find_complement(scored_venues, ["General"], exclude_names=[anchor['name']], anchor=anchor)
            if s2_venue:
                s2 = self._create_stop(s2_venue, "Wander nearby", "03:30 PM", used_images)
                plan.append(s2)
                used_images.append(s2['postgres_data']['photos'][0])
                
                s3_venue = self._find_complement(scored_venues, ["General"], exclude_names=[anchor['name'], s2_venue['name']], anchor=anchor)
                if s3_venue:
                    s3 = self._create_stop(s3_venue, "Final stop", "05:00 PM", used_images)
                    plan.append(s3)
                    used_images.append(s3['postgres_data']['photos'][0])

        # 4. CONCIERGE COPYWRITING ENGINE
        vibe_key = selected_vibe.lower()
        neighborhood = anchor.get('neighborhood') or "the neighborhood"
        
        # Calculate estimated walk time
        total_dist = 0
        if len(plan) > 1:
            for i in range(len(plan)-1):
                total_dist += self._get_distance(plan[i]['postgres_data']['lat'], plan[i]['postgres_data']['lng'], 
                                              plan[i+1]['postgres_data']['lat'], plan[i+1]['postgres_data']['lng'])
        total_mins = max(5, int(total_dist * 12)) 
        walk_word = "stroll" if total_mins < 15 else "walk"

        # --- Dynamic Title Templates ---
        title_templates = [
            f"The {selected_vibe.title()} Edit: {anchor['name']}",
            f"{anchor['name']} & Hidden Gems",
            f"Curated: {anchor['name']}",
            f"Essential {neighborhood} {selected_vibe.title()}",
            f"The {selected_vibe.title()} Route: {anchor['name']}"
        ]
        
        if vibe_key == 'coffee':
            title_templates += [f"Morning Rituals: {anchor['name']}", f"Caffeine & Culture"]
        elif vibe_key == 'nightlife':
            title_templates += [f"Nights at {anchor['name']}", "After Hours Edit"]
        elif vibe_key == 'arts':
            title_templates += [f"Gallery Walk: {anchor['name']}", "Creative Pulse"]

        # --- Dynamic Subtitle Templates ---
        subtitle_templates = [
            f"{len(plan)} curated stops • {total_mins} min {walk_word}",
            f"A curated trio • Perfectly walkable",
            f"Handpicked itinerary • Easy pace",
            f"A bespoke route • Walk Score: 98",
            f"The {vibe_key} collection • {neighborhood.title()}"
        ]

        # --- IMAGE LOGIC: Force Food Only for Header ---
        header_image_url = "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=800" # Default
        
        if image_service:
            # 1. Determine a strict food keyword based on the anchor
            hero_food_query = self._get_hero_food_query(anchor['name'], anchor.get('category', 'General'))
            
            print(f"[ItineraryEngine] Fetching HERO image using strict query: '{hero_food_query}'")
            
            # 2. Call image service with specific food query to avoid people/interiors
            header_image_url = image_service.get_venue_image(
                venue_name=hero_food_query,  # Trick service to search for the food, not the place
                category="Food",             # Force category
                vibe="food photography close up delicious", # Force macro style
                exclude_urls=used_images
            )

        return {
            "title": random.choice(title_templates),
            "subtitle": random.choice(subtitle_templates),
            "walk_time_text": f"{total_mins} min {walk_word}",
            "tags": [selected_vibe.lower(), "walkable"],
            "sample_image_url": header_image_url, 
            "itinerary_data": {
                "itinerary": plan,
                "anchor": anchor
            }
        }

    def _category_to_vibe(self, category: str) -> str:
        """
        Map raw category strings to one of 4 vibe buckets.
        Used for strict vibe filtering.
        """
        if not category:
            return 'food'
        cat = category.lower()
        
        # Nightlife keywords
        if any(k in cat for k in ['bar', 'club', 'cocktail', 'lounge', 'wine', 'speakeasy', 'pub', 'nightclub', 'beer', 'brewery', 'spirit']):
            return 'nightlife'
        
        # Coffee/Cafe keywords
        if any(k in cat for k in ['coffee', 'cafe', 'café', 'bakery', 'tea', 'brunch', 'breakfast', 'pastry', 'donut', 'bagel']):
            return 'coffee'
        
        # Arts/Culture keywords
        if any(k in cat for k in ['gallery', 'museum', 'art', 'theater', 'theatre', 'park', 'garden', 'culture', 'music', 'landmark', 'historic']):
            return 'arts'
        
        # Default to food
        return 'food'

    def _get_hero_food_query(self, venue_name: str, category: str) -> str:
        """
        Returns a specific food search term based on venue details 
        to ensure we get appetizing food pics, not people.
        """
        name_lower = venue_name.lower()
        cat_lower = category.lower()

        # Specific Name Triggers
        if "bagel" in name_lower: return "bagel sandwich with cream cheese"
        if "pizza" in name_lower: return "gourmet pizza slice"
        if "sushi" in name_lower or "omakase" in name_lower: return "sushi platter close up"
        if "pasta" in name_lower: return "fresh pasta dish"
        if "burger" in name_lower: return "juicy burger"
        if "taco" in name_lower: return "tacos close up"
        if "dim sum" in name_lower: return "dim sum basket"
        if "ramen" in name_lower: return "ramen bowl"
        if "steak" in name_lower: return "steak dinner"

        # Category Triggers
        if "coffee" in cat_lower or "cafe" in cat_lower: return "latte art coffee cup"
        if "bakery" in cat_lower or "pastry" in cat_lower: return "croissant and pastry"
        if "dessert" in cat_lower or "ice cream" in cat_lower: return "gourmet dessert close up"
        if "bar" in cat_lower or "cocktail" in cat_lower: return "fancy cocktail drink close up"
        if "brunch" in cat_lower: return "avocado toast brunch"
        
        # Fallbacks
        if "asian" in cat_lower: return "asian dumplings food"
        if "italian" in cat_lower: return "italian pasta dish"
        if "mexican" in cat_lower: return "mexican food feast"
        
        # Generic safe fallbacks (never people)
        return "delicious gourmet dish close up"

    def _find_complement(self, scored_list: List[Tuple], categories: List[str], exclude_names: List[str], anchor: Dict) -> Optional[Dict]:
        """
        Finds a suitable secondary stop based on category and proximity to the anchor.
        """
        pool = []
        for _, venue in scored_list:
            if venue['name'] in exclude_names: continue
            
            # Check for category match or generic fallback
            if venue['category'] in categories or "General" in categories:
                dist_to_anchor = self._get_distance(anchor['lat'], anchor['lng'], venue['lat'], venue['lng'])
                
                if dist_to_anchor < 1.0:
                    select_score = 100 - (dist_to_anchor * 50) 
                    pool.append((select_score, venue))
        
        if not pool:
            for _, venue in scored_list:
                if venue['name'] in exclude_names: continue
                dist_to_anchor = self._get_distance(anchor['lat'], anchor['lng'], venue['lat'], venue['lng'])
                if dist_to_anchor < 1.0:
                    pool.append((50, venue))

        if pool:
            pool.sort(key=lambda x: x[0], reverse=True)
            top_tier = pool[:3]
            return random.choice(top_tier)[1]
            
        return None

    def _create_stop(self, venue: Dict, label: str, time: str, exclude_urls: List[str] = None) -> Dict:
        # Fetch dynamic image from Pexels (with caching)
        if image_service:
            # We also sanitize the stop images slightly to prefer food/interior over crowds
            clean_query = self._get_hero_food_query(venue['name'], venue.get('category', 'General'))
            
            photo_url = image_service.get_venue_image(
                venue_name=clean_query, # Use the food item name, not the venue name
                category=venue.get('category', 'Restaurant'),
                vibe="food detail", # Force detail shots
                exclude_urls=exclude_urls
            )
        else:
            photo_url = "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=400"

        return {
            "time": time,
            "place_name": venue['name'],
            "ai_notes": f"{label}. {venue['description'][:100]}...",
            "postgres_data": {
                "name": venue['name'],
                "lat": venue['lat'],
                "lng": venue['lng'],
                "rating": venue['rating'],
                "category": venue.get('category', 'General'),
                "description": venue.get('description', ''),
                "photos": [photo_url],
            }
        }

    def _get_distance(self, lat1, lon1, lat2, lon2):
        R = 6371 
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
