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
                'title': 'La Dolce Vita: East Village Italian Journey',
                'description': 'Discover authentic Italian trattorias and hidden neighborhood gems where traditional recipes meet East Village charm.',
                'cuisine': 'Italian',
                'price_range': '$30 and under',
                'tags': ['Neighborhood gem'],
                'neighborhood': 'East Village',
                'radius_km': 1.0,
                'is_featured': True,
            },
            {
                'title': 'Parisian Elegance in TriBeCa',
                'description': 'Experience the sophisticated allure of French dining in TriBeCa\'s elegant restaurants, where classic techniques meet modern innovation.',
                'cuisine': 'French',
                'price_range': '$31-$50',
                'tags': ['Charming'],
                'neighborhood': 'TriBeCa',
                'radius_km': 3.0,
                'is_featured': True,
            },
            {
                'title': 'West Village Fiesta',
                'description': 'Savor vibrant Mexican flavors in the heart of the West Village, where festive cantinas and authentic taquerias create unforgettable group dining experiences.',
                'cuisine': 'Mexican',
                'price_range': '$30 and under',
                'tags': ['Good for groups'],
                'neighborhood': 'West Village',
                'radius_km': 1.0,
                'is_featured': True,
            },
            {
                'title': 'Omakase Experience: Lower East Side',
                'description': 'Discover exceptional Japanese dining in the Lower East Side, where omakase experiences and innovative izakayas redefine fine dining.',
                'cuisine': 'Japanese',
                'price_range': '$50+',
                'tags': ['Good for special occasions'],
                'neighborhood': 'Lower East Side',
                'radius_km': 3.0,
                'is_featured': True,
            },
            {
                'title': 'SoHo Brunch Scene',
                'description': 'Start your weekend right with SoHo\'s most celebrated brunch spots, where innovative American cuisine meets the neighborhood\'s artistic energy.',
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

