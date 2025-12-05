"""
Django management command to generate pre-created itineraries using intelligent algorithm.
Run with: python manage.py generate_pre_created_itineraries
"""
"""
Django management command to generate pre-created itineraries using intelligent algorithm.
Run with: python manage.py generate_pre_created_itineraries
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from res_backend.models import PreCreatedItinerary, ScrapedRestaurant
from res_backend.utils import (
    query_scraped_restaurants,
    calculate_restaurant_score,
    ensure_diversity,
    optimize_route,
    calculate_route_distance,
    haversine_distance
)
import math
import random
from collections import defaultdict


class Command(BaseCommand):
    help = 'Generate pre-created itineraries using intelligent algorithm'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of itineraries to generate',
        )
        parser.add_argument(
            '--min-restaurants',
            type=int,
            default=8,
            help='Minimum restaurants required per itinerary',
        )
        parser.add_argument(
            '--max-restaurants',
            type=int,
            default=10,
            help='Maximum restaurants per itinerary',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        min_restaurants = options['min_restaurants']
        max_restaurants = options['max_restaurants']
        
        self.stdout.write(self.style.SUCCESS('Starting itinerary generation...'))
        
        # Get all category combinations
        category_combinations = self._get_category_combinations()
        
        # Get locations (fixed neighborhoods + dynamic clusters)
        locations = self._get_locations()
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for location in locations:
            lat = location['latitude']
            lng = location['longitude']
            neighborhood = location.get('neighborhood', 'Dynamic Cluster')
            radius_km = location.get('radius_km', 3.0)
            
            self.stdout.write(f'\nProcessing location: {neighborhood} ({lat}, {lng})')
            
            for combo in category_combinations:
                if created_count + updated_count >= limit:
                    break
                
                try:
                    result = self._generate_itinerary_for_category(
                        lat, lng, radius_km, combo, min_restaurants, max_restaurants
                    )
                    
                    if result:
                        itinerary_data, stats = result
                        
                        # Check if itinerary already exists
                        existing = PreCreatedItinerary.objects.filter(
                            cuisine=combo.get('cuisine', ''),
                            price_range=combo.get('price_range', ''),
                            neighborhood=neighborhood,
                            latitude=lat,
                            longitude=lng
                        ).first()
                        
                        if existing:
                            # Update existing
                            existing.title = combo['title']
                            existing.description = combo['description']
                            existing.tags = combo.get('tags', [])
                            existing.radius_km = radius_km
                            existing.itinerary_data = itinerary_data
                            existing.total_restaurants = stats['total_restaurants']
                            existing.enriched_count = stats['enriched_count']
                            existing.enrichment_percentage = stats['enrichment_percentage']
                            existing.is_featured = stats.get('is_featured', False)
                            existing.sample_image_url = stats.get('sample_image_url', '')
                            existing.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  Updated: {combo["title"]}')
                            )
                        else:
                            # Create new
                            PreCreatedItinerary.objects.create(
                                title=combo['title'],
                                description=combo['description'],
                                cuisine=combo.get('cuisine', ''),
                                price_range=combo.get('price_range', ''),
                                min_rating=combo.get('min_rating', 4.0),
                                tags=combo.get('tags', []),
                                latitude=lat,
                                longitude=lng,
                                radius_km=radius_km,
                                neighborhood=neighborhood,
                                itinerary_data=itinerary_data,
                                total_restaurants=stats['total_restaurants'],
                                enriched_count=stats['enriched_count'],
                                enrichment_percentage=stats['enrichment_percentage'],
                                is_featured=stats.get('is_featured', False),
                                sample_image_url=stats.get('sample_image_url', ''),
                            )
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'  Created: {combo["title"]}')
                            )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'  Skipped: {combo["title"]} (insufficient restaurants)')
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  Error creating {combo["title"]}: {str(e)}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n\nCompleted: Created {created_count}, Updated {updated_count}, Skipped {skipped_count}'
            )
        )

    def _get_category_combinations(self):
        """Define all category combinations to generate."""
        cuisines = [
            'Italian', 'French', 'Mexican', 'Japanese', 'Chinese', 'Thai',
            'Indian', 'Mediterranean', 'American', 'Korean', 'Spanish', 'Greek'
        ]
        
        price_ranges = ['$30 and under', '$31-$50', '$50+']
        
        occasions = [
            {'name': 'Date Night', 'tags': ['Romantic', 'Upscale'], 'price_bias': '$50+'},
            {'name': 'Group Dining', 'tags': ['Good for groups'], 'price_bias': None},
            {'name': 'Brunch', 'tags': ['Great for brunch'], 'price_bias': '$31-$50'},
            {'name': 'Business Lunch', 'tags': [], 'price_bias': '$31-$50'},
            {'name': 'Late Night', 'tags': ['Late night'], 'price_bias': None},
            {'name': 'Family Friendly', 'tags': ['Family friendly'], 'price_bias': '$30 and under'},
        ]
        
        special_features = [
            'Outdoor Seating', 'Live Music', 'Vegetarian-Friendly', 
            'Pet-Friendly', 'Romantic', 'Good for groups'
        ]
        
        combinations = []
        
        # Cuisine + Price combinations
        for cuisine in cuisines[:8]:  # Top 8 cuisines
            for price_range in price_ranges:
                combinations.append({
                    'title': f'{cuisine} Food Tour',
                    'description': f'Discover the best {cuisine.lower()} restaurants',
                    'cuisine': cuisine,
                    'price_range': price_range,
                    'tags': [],
                    'min_rating': 4.0,
                })
        
        # Occasion-based combinations
        for occasion in occasions:
            price_range = occasion['price_bias'] or random.choice(price_ranges)
            cuisine = random.choice(cuisines[:6])  # Top 6 cuisines for occasions
            
            combinations.append({
                'title': f'{occasion["name"]} - {cuisine}',
                'description': f'Perfect {occasion["name"].lower()} spots',
                'cuisine': cuisine,
                'price_range': price_range,
                'tags': occasion['tags'],
                'min_rating': 4.0,
            })
        
        # Special feature combinations
        for feature in special_features[:4]:  # Top 4 features
            cuisine = random.choice(cuisines[:6])
            price_range = random.choice(price_ranges)
            
            combinations.append({
                'title': f'{feature} Restaurants',
                'description': f'Restaurants with {feature.lower()}',
                'cuisine': cuisine,
                'price_range': price_range,
                'tags': [feature],
                'min_rating': 4.0,
            })
        
        # Neighborhood-specific (no cuisine filter)
        combinations.append({
            'title': 'Neighborhood Food Tour',
            'description': 'Explore the best local spots',
            'cuisine': '',  # No specific cuisine
            'price_range': '',  # Mixed prices
            'tags': ['Neighborhood gem'],
            'min_rating': 4.0,
        })
        
        return combinations

    def _get_locations(self):
        """Get locations: fixed neighborhoods + dynamic clusters."""
        locations = []
        
        # Fixed popular neighborhoods
        fixed_neighborhoods = {
            'East Village': (40.7262, -73.9818, 1.0),
            'TriBeCa': (40.7181, -74.0086, 3.0),
            'West Village': (40.7358, -74.0036, 1.0),
            'Lower East Side': (40.7150, -73.9843, 3.0),
            'SoHo': (40.7231, -74.0026, 1.0),
            'Chelsea': (40.7465, -74.0014, 2.0),
            'Upper West Side': (40.7870, -73.9754, 2.0),
            'Greenwich Village': (40.7336, -74.0027, 1.5),
        }
        
        for name, (lat, lng, radius) in fixed_neighborhoods.items():
            locations.append({
                'neighborhood': name,
                'latitude': lat,
                'longitude': lng,
                'radius_km': radius,
            })
        
        # Find dynamic clusters
        clusters = self._find_restaurant_clusters(min_restaurants=15, radius_km=2.0)
        for cluster in clusters[:5]:  # Top 5 clusters
            locations.append({
                'neighborhood': f'Restaurant Cluster {cluster["id"]}',
                'latitude': cluster['center_lat'],
                'longitude': cluster['center_lng'],
                'radius_km': cluster['radius_km'],
            })
        
        return locations

    def _find_restaurant_clusters(self, min_restaurants=15, radius_km=2.0):
        """
        Find restaurant clusters using simple grid-based clustering.
        More sophisticated than DBSCAN but simpler to implement.
        """
        # Get all restaurants with coordinates
        restaurants = ScrapedRestaurant.objects.filter(
            is_active=True,
            duplicate_of__isnull=True,
            latitude__isnull=False,
            longitude__isnull=False
        ).values_list('latitude', 'longitude')
        
        if not restaurants:
            return []
        
        # Convert to list of tuples
        coords = [(float(lat), float(lng)) for lat, lng in restaurants]
        
        # Simple grid-based clustering
        # Divide area into grid cells and find dense cells
        grid_size = 0.01  # ~1km grid cells
        
        # Find bounds
        lats = [c[0] for c in coords]
        lngs = [c[1] for c in coords]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        
        # Create grid
        grid = defaultdict(list)
        for lat, lng in coords:
            grid_x = int((lat - min_lat) / grid_size)
            grid_y = int((lng - min_lng) / grid_size)
            grid[(grid_x, grid_y)].append((lat, lng))
        
        # Find dense cells
        clusters = []
        for (gx, gy), points in grid.items():
            if len(points) >= min_restaurants:
                # Calculate center
                center_lat = sum(p[0] for p in points) / len(points)
                center_lng = sum(p[1] for p in points) / len(points)
                
                clusters.append({
                    'id': len(clusters) + 1,
                    'center_lat': center_lat,
                    'center_lng': center_lng,
                    'restaurant_count': len(points),
                    'radius_km': radius_km,
                })
        
        # Sort by restaurant count
        clusters.sort(key=lambda x: x['restaurant_count'], reverse=True)
        
        return clusters

    def _generate_itinerary_for_category(self, lat, lng, radius_km, category_filters, 
                                         min_restaurants, max_restaurants):
        """
        Generate itinerary for a specific category combination.
        
        Returns:
            Tuple of (itinerary_data dict, stats dict) or None if insufficient restaurants
        """
        # Build filters
        filters = {
            'min_rating': category_filters.get('min_rating', 4.0),
        }
        
        if category_filters.get('cuisine'):
            filters['cuisine'] = category_filters['cuisine']
        
        if category_filters.get('price_range'):
            filters['price_range'] = category_filters['price_range']
        
        if category_filters.get('tags'):
            filters['tags'] = category_filters['tags']
        
        # Query restaurants from Supabase (first try with coordinates required)
        restaurants = query_scraped_restaurants(lat, lng, radius_km, filters, require_coordinates=True)
        
        # If not enough restaurants, try without some filters
        if len(restaurants) < min_restaurants:
            # Try without cuisine filter
            if filters.get('cuisine'):
                relaxed_filters = filters.copy()
                del relaxed_filters['cuisine']
                restaurants = query_scraped_restaurants(lat, lng, radius_km, relaxed_filters, require_coordinates=True)
        
        # If still not enough, try without requiring coordinates (city/state matching)
        if len(restaurants) < min_restaurants:
            # Get city from a sample restaurant or use NYC as default
            # Try with city-based matching instead of coordinates
            city_filters = filters.copy()
            # Remove geospatial requirement, use city matching
            restaurants = query_scraped_restaurants(lat, lng, radius_km, city_filters, require_coordinates=False)
            # Filter by city name (NYC neighborhoods)
            city_name = self._get_city_from_location(lat, lng)
            if city_name:
                restaurants = [r for r in restaurants if 'new york' in (r.city or '').lower() or 'nyc' in (r.city or '').lower()]
        
        # Google Places API fallback (if still not enough)
        if len(restaurants) < min_restaurants:
            # Note: Google Places API fallback would be implemented here
            # For now, we'll use a more relaxed filter approach
            # In production, this could call Google Places API and match with Supabase
            
            # Try with minimal filters (just rating, no location requirement)
            minimal_filters = {
                'min_rating': filters.get('min_rating', 3.5),  # Lower threshold
            }
            # Get all restaurants with minimal filters (no location constraint)
            all_restaurants = ScrapedRestaurant.objects.filter(
                is_active=True,
                duplicate_of__isnull=True,
                rating__gte=minimal_filters['min_rating']
            )[:max_restaurants * 3]  # Get more candidates
            
            # Score and select best ones
            scored = [(r, calculate_restaurant_score(r, minimal_filters)) for r in all_restaurants]
            scored.sort(key=lambda x: x[1], reverse=True)
            restaurants = [r for r, s in scored[:max_restaurants * 2]]
            
            # If still not enough, skip this combination
            # In future: Could call Google Places API here via API endpoint
            if len(restaurants) < min_restaurants:
                return None
        
        # Score restaurants
        scored_restaurants = []
        for restaurant in restaurants:
            score = calculate_restaurant_score(restaurant, filters)
            scored_restaurants.append((restaurant, score))
        
        # Sort by score
        scored_restaurants.sort(key=lambda x: x[1], reverse=True)
        
        # Apply diversity constraints
        top_restaurants = [r for r, s in scored_restaurants[:max_restaurants * 2]]
        diverse_restaurants = ensure_diversity(top_restaurants, max_same_cuisine=2, max_same_price=3)
        
        # Select final restaurants (8-10)
        selected_restaurants = diverse_restaurants[:max_restaurants]
        
        if len(selected_restaurants) < min_restaurants:
            return None
        
        # Optimize route (only if restaurants have coordinates)
        restaurants_with_coords = [r for r in selected_restaurants if r.latitude and r.longitude]
        restaurants_without_coords = [r for r in selected_restaurants if not (r.latitude and r.longitude)]
        
        if restaurants_with_coords:
            optimized_route = optimize_route(restaurants_with_coords, lat, lng, max_distance_between=1.0)
            # Add restaurants without coordinates at the end
            optimized_route.extend(restaurants_without_coords)
        else:
            # No coordinates available, use original order
            optimized_route = selected_restaurants
        
        # Assign to time slots
        time_slots = self._create_time_slots(optimized_route)
        
        # Build itinerary data
        itinerary_items = []
        enriched_count = 0
        
        for slot_name, slot_restaurants in time_slots.items():
            for restaurant in slot_restaurants:
                # Convert restaurant to itinerary item format
                item = {
                    'place_name': restaurant.name,
                    'address': restaurant.address,
                    'latitude': float(restaurant.latitude) if restaurant.latitude else None,
                    'longitude': float(restaurant.longitude) if restaurant.longitude else None,
                    'rating': float(restaurant.rating) if restaurant.rating else 0.0,
                    'price_range': restaurant.price_range or '',
                    'time_slot': slot_name,
                    'is_enriched': True,  # All from Supabase are enriched
                    'postgres_data': {
                        'menu_items': restaurant.menu_items if restaurant.menu_items else [],
                        'reviews': restaurant.raw_data.get('reviews', []) if restaurant.raw_data else [],
                        'tags': restaurant.raw_data.get('tags', []) if restaurant.raw_data else [],
                        'features': restaurant.features if restaurant.features else [],
                        'photos': restaurant.photos if restaurant.photos else [],
                        'about': restaurant.description or '',
                        'price_range': restaurant.price_range,
                        'hours': restaurant.hours if restaurant.hours else {},
                        'categories': restaurant.categories if restaurant.categories else [],
                        'phone': restaurant.phone,
                        'website': restaurant.website,
                    },
                    'enrichment_metadata': {
                        'has_menu': len(restaurant.menu_items) > 0 if restaurant.menu_items else False,
                        'has_reviews': len(restaurant.raw_data.get('reviews', [])) > 0 if restaurant.raw_data else False,
                        'has_tags': len(restaurant.raw_data.get('tags', [])) > 0 if restaurant.raw_data else False,
                        'data_quality_score': restaurant.data_quality_score,
                    },
                }
                itinerary_items.append(item)
                enriched_count += 1
        
        # Calculate statistics
        total_restaurants = len(itinerary_items)
        enrichment_percentage = 100.0  # All from Supabase
        # Calculate distance only for restaurants with coordinates
        route_with_coords = [r for r in optimized_route if r.latitude and r.longitude]
        total_distance = calculate_route_distance(route_with_coords) if route_with_coords else 0.0
        avg_rating = sum(float(r.rating or 0) for r in optimized_route) / len(optimized_route) if optimized_route else 0
        
        # Get sample image
        sample_image_url = ''
        for restaurant in optimized_route:
            if restaurant.photos and len(restaurant.photos) > 0:
                sample_image_url = restaurant.photos[0] if isinstance(restaurant.photos[0], str) else ''
                break
        
        # Determine if featured
        is_featured = (
            enrichment_percentage > 50 and
            avg_rating > 4.0 and
            total_distance < 5.0 and
            total_restaurants >= min_restaurants
        )
        
        itinerary_data = {
            'itinerary': itinerary_items,
            'enrichment_stats': {
                'total_restaurants': total_restaurants,
                'enriched_count': enriched_count,
                'enrichment_percentage': enrichment_percentage,
            },
            'route_stats': {
                'total_distance_km': round(total_distance, 2),
                'avg_distance_between': round(total_distance / max(1, total_restaurants - 1), 2),
            },
        }
        
        stats = {
            'total_restaurants': total_restaurants,
            'enriched_count': enriched_count,
            'enrichment_percentage': enrichment_percentage,
            'is_featured': is_featured,
            'sample_image_url': sample_image_url,
        }
        
        return (itinerary_data, stats)

    def _create_time_slots(self, restaurants):
        """
        Assign restaurants to time slots based on type and optimal distribution.
        
        Returns:
            Dict with time slot names as keys and lists of restaurants as values
        """
        time_slots = {
            'morning': [],
            'mid_day': [],
            'afternoon': [],
            'evening': [],
        }
        
        if not restaurants:
            return time_slots
        
        # Categorize restaurants
        cafes_bakeries = []
        casual_dining = []
        fine_dining = []
        others = []
        
        for restaurant in restaurants:
            categories = [c.lower() for c in (restaurant.categories or [])]
            name_lower = restaurant.name.lower()
            
            # Check for cafe/bakery/brunch
            if (any('cafe' in c or 'bakery' in c or 'brunch' in c for c in categories) or
                'cafe' in name_lower or 'bakery' in name_lower or 'brunch' in name_lower):
                cafes_bakeries.append(restaurant)
            # Check for fine dining
            elif (restaurant.price_range in ['$$$$', '$$$$$'] or
                  any('fine' in c or 'upscale' in c for c in categories)):
                fine_dining.append(restaurant)
            # Casual dining
            else:
                casual_dining.append(restaurant)
        
        # Distribute evenly
        total = len(restaurants)
        per_slot = max(1, total // 4)
        
        # Morning: cafes/bakeries first
        time_slots['morning'] = cafes_bakeries[:per_slot]
        remaining_cafes = cafes_bakeries[per_slot:]
        
        # Mid-day: casual dining
        time_slots['mid_day'] = casual_dining[:per_slot]
        remaining_casual = casual_dining[per_slot:]
        
        # Afternoon: remaining cafes or casual
        afternoon_pool = remaining_cafes + remaining_casual[:per_slot]
        time_slots['afternoon'] = afternoon_pool[:per_slot]
        remaining_afternoon = afternoon_pool[per_slot:]
        
        # Evening: fine dining first, then remaining
        evening_pool = fine_dining + remaining_casual[per_slot:] + remaining_afternoon
        time_slots['evening'] = evening_pool[:per_slot]
        
            # Distribute any remaining restaurants
        all_assigned = (time_slots['morning'] + time_slots['mid_day'] + 
                       time_slots['afternoon'] + time_slots['evening'])
        remaining = [r for r in restaurants if r not in all_assigned]
        
        # Add remaining to slots that need more
        slot_order = ['morning', 'mid_day', 'afternoon', 'evening']
        for i, restaurant in enumerate(remaining):
            slot = slot_order[i % len(slot_order)]
            time_slots[slot].append(restaurant)
        
        return time_slots

    def _get_city_from_location(self, lat, lng):
        """Get city name from coordinates (simplified for NYC)."""
        # NYC bounding box
        if 40.4774 <= lat <= 40.9176 and -74.2591 <= lng <= -73.7004:
            return 'New York'
        return None

