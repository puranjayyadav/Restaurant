"""
Django management command to pre-create featured itineraries.
Run with: python manage.py pre_create_itineraries
"""
from django.core.management.base import BaseCommand
from res_backend.models import PreCreatedItinerary


class Command(BaseCommand):
    help = 'Pre-create featured itineraries for discovery page'

    def handle(self, *args, **options):
        # Popular NYC neighborhood coordinates
        neighborhoods = {
            'East Village': (40.7262, -73.9818),
            'TriBeCa': (40.7181, -74.0086),
            'West Village': (40.7358, -74.0036),
            'Lower East Side': (40.7150, -73.9843),
            'SoHo': (40.7231, -74.0026),
        }
        
        # Popular combinations to pre-create
        combinations = [
            {
                'title': 'Italian Food Tour in East Village',
                'description': 'Discover authentic Italian restaurants and neighborhood gems',
                'cuisine': 'Italian',
                'price_range': '$30 and under',
                'tags': ['Neighborhood gem'],
                'neighborhood': 'East Village',
                'radius_km': 1.0,
                'is_featured': True,
            },
            {
                'title': 'Charming French Dining in TriBeCa',
                'description': 'Elegant French restaurants perfect for a special evening',
                'cuisine': 'French',
                'price_range': '$31-$50',
                'tags': ['Charming'],
                'neighborhood': 'TriBeCa',
                'radius_km': 3.0,
                'is_featured': True,
            },
            {
                'title': 'Mexican Fiesta in West Village',
                'description': 'Vibrant Mexican spots great for groups',
                'cuisine': 'Mexican',
                'price_range': '$30 and under',
                'tags': ['Good for groups'],
                'neighborhood': 'West Village',
                'radius_km': 1.0,
                'is_featured': True,
            },
            {
                'title': 'Upscale Japanese Dining in Lower East Side',
                'description': 'Fine Japanese restaurants for special occasions',
                'cuisine': 'Japanese',
                'price_range': '$50+',
                'tags': ['Good for special occasions'],
                'neighborhood': 'Lower East Side',
                'radius_km': 3.0,
                'is_featured': True,
            },
            {
                'title': 'Brunch Spots in SoHo',
                'description': 'Contemporary American brunch favorites',
                'cuisine': 'Contemporary American',
                'price_range': '$31-$50',
                'tags': ['Great for brunch'],
                'neighborhood': 'SoHo',
                'radius_km': 1.0,
                'is_featured': True,
            },
        ]
        
        created_count = 0
        updated_count = 0
        errors = []
        
        for combo in combinations:
            try:
                # Get neighborhood coordinates
                if combo['neighborhood'] not in neighborhoods:
                    errors.append(f"Unknown neighborhood: {combo['neighborhood']}")
                    continue
                
                lat, lng = neighborhoods[combo['neighborhood']]
                
                # Check if itinerary already exists
                existing = PreCreatedItinerary.objects.filter(
                    cuisine=combo['cuisine'],
                    price_range=combo['price_range'],
                    neighborhood=combo['neighborhood'],
                    latitude=lat,
                    longitude=lng
                ).first()
                
                if existing:
                    # Update existing
                    existing.title = combo['title']
                    existing.description = combo['description']
                    existing.tags = combo['tags']
                    existing.radius_km = combo['radius_km']
                    existing.is_featured = combo['is_featured']
                    existing.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Updated: {combo["title"]}')
                    )
                    continue
                
                # Create new
                itinerary = PreCreatedItinerary.objects.create(
                    title=combo['title'],
                    description=combo['description'],
                    cuisine=combo['cuisine'],
                    price_range=combo['price_range'],
                    min_rating=4.0,
                    tags=combo['tags'],
                    latitude=lat,
                    longitude=lng,
                    radius_km=combo['radius_km'],
                    neighborhood=combo['neighborhood'],
                    itinerary_data={},  # Empty - will be populated when generated
                    total_restaurants=0,
                    enriched_count=0,
                    enrichment_percentage=0,
                    is_featured=combo['is_featured'],
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created: {combo["title"]}')
                )
                
            except Exception as e:
                error_msg = f"Error creating {combo['title']}: {str(e)}"
                errors.append(error_msg)
                self.stdout.write(
                    self.style.ERROR(error_msg)
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} and updated {updated_count} pre-created itineraries'
            )
        )
        if errors:
            self.stdout.write(
                self.style.WARNING(f'\nErrors: {len(errors)}')
            )

