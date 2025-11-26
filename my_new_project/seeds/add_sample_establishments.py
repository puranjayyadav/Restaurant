import sys
import os
import django
import random

# Configure Django settings
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_new_project.settings')
django.setup()

# Import Django models after setup
from django.contrib.auth.models import User
from res_backend.models import Establishment, EstablishmentFeature

def create_test_user():
    """Create a test user if not exists"""
    if not User.objects.filter(username='testuser').exists():
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        print(f"Created test user with ID: {user.id}")
        return user
    else:
        user = User.objects.get(username='testuser')
        print(f"Using existing test user with ID: {user.id}")
        return user

def add_sample_establishments(user):
    """Add sample establishments for testing recommendations"""
    
    # Sample data - original set
    restaurants = [
        {
            'name': 'Taste of Italy',
            'address': '123 Main St, New York, NY',
            'price_range': '$$$',
            'dining_style': 'FINE',
            'location_region': 'New York',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'features': ['OUTDOOR', 'VEGAN']
        },
        {
            'name': 'Burger Palace',
            'address': '456 Oak Ave, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7308,
            'longitude': -73.9973,
            'features': ['TAKEOUT', 'FAMILY']
        },
        {
            'name': 'Sushi Heaven',
            'address': '789 Pine St, New York, NY',
            'price_range': '$$$$',
            'dining_style': 'FINE',
            'location_region': 'New York',
            'latitude': 40.7580,
            'longitude': -73.9855,
            'features': ['VEGAN', 'HALAL']
        },
        {
            'name': 'Quick Bites Cafe',
            'address': '101 Elm St, New York, NY',
            'price_range': '$',
            'dining_style': 'CAFE',
            'location_region': 'New York',
            'latitude': 40.7425,
            'longitude': -74.0060,
            'features': ['TAKEOUT', 'OUTDOOR']
        },
        {
            'name': 'BBQ Master',
            'address': '202 Maple Ave, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7225,
            'longitude': -73.9890,
            'features': ['FAMILY', 'LATE']
        }
    ]
    
    # Add more diverse restaurants
    additional_restaurants = [
        {
            'name': 'Taco Fiesta',
            'address': '300 Broadway, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7250,
            'longitude': -73.9950,
            'features': ['TAKEOUT', 'OUTDOOR', 'FAMILY'],
            'types': ['mexican', 'taco', 'restaurant']
        },
        {
            'name': 'Pho Delight',
            'address': '450 Canal St, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7200,
            'longitude': -74.0050,
            'features': ['TAKEOUT', 'VEGAN'],
            'types': ['vietnamese', 'soup', 'asian', 'restaurant']
        },
        {
            'name': 'Indian Spice Kitchen',
            'address': '555 5th Ave, New York, NY',
            'price_range': '$$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7400,
            'longitude': -73.9800,
            'features': ['DELIVERY', 'VEGAN', 'SPICY'],
            'types': ['indian', 'curry', 'spicy', 'restaurant']
        },
        {
            'name': 'Mama\'s Pizza',
            'address': '123 Mulberry St, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7190,
            'longitude': -73.9970,
            'features': ['TAKEOUT', 'FAMILY', 'DELIVERY'],
            'types': ['pizza', 'italian', 'restaurant']
        },
        {
            'name': 'The Gourmet Burger',
            'address': '789 7th Ave, New York, NY',
            'price_range': '$$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7620,
            'longitude': -73.9820,
            'features': ['GOURMET', 'OUTDOOR'],
            'types': ['burger', 'gourmet', 'restaurant']
        },
        {
            'name': 'Fusion Sushi Bar',
            'address': '222 E 14th St, New York, NY',
            'price_range': '$$$',
            'dining_style': 'MODERN',
            'location_region': 'New York',
            'latitude': 40.7320,
            'longitude': -73.9870,
            'features': ['ALCOHOL', 'MODERN', 'LATE'],
            'types': ['sushi', 'japanese', 'fusion', 'restaurant']
        },
        {
            'name': 'Parisian Cafe',
            'address': '444 W 23rd St, New York, NY',
            'price_range': '$$',
            'dining_style': 'CAFE',
            'location_region': 'New York',
            'latitude': 40.7470,
            'longitude': -74.0020,
            'features': ['OUTDOOR', 'BREAKFAST', 'COFFEE'],
            'types': ['cafe', 'french', 'breakfast', 'coffee']
        },
        {
            'name': 'Mediterranean Delights',
            'address': '678 9th Ave, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7580,
            'longitude': -73.9910,
            'features': ['HEALTHY', 'VEGAN', 'OUTDOOR'],
            'types': ['mediterranean', 'greek', 'healthy', 'restaurant']
        },
        {
            'name': 'Steakhouse Prime',
            'address': '890 Park Ave, New York, NY',
            'price_range': '$$$$',
            'dining_style': 'FINE',
            'location_region': 'New York',
            'latitude': 40.7740,
            'longitude': -73.9640,
            'features': ['UPSCALE', 'ALCOHOL', 'RESERVATION'],
            'types': ['steakhouse', 'fine_dining', 'american', 'restaurant']
        },
        {
            'name': 'Ramen House',
            'address': '111 E 31st St, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7460,
            'longitude': -73.9810,
            'features': ['TAKEOUT', 'LATE'],
            'types': ['ramen', 'japanese', 'noodles', 'restaurant']
        },
        {
            'name': 'Vegan Paradise',
            'address': '333 W 4th St, New York, NY',
            'price_range': '$$$',
            'dining_style': 'MODERN',
            'location_region': 'New York',
            'latitude': 40.7350,
            'longitude': -74.0030,
            'features': ['VEGAN', 'ORGANIC', 'HEALTHY'],
            'types': ['vegan', 'vegetarian', 'healthy', 'restaurant']
        },
        {
            'name': 'Coffee & Books',
            'address': '555 Broadway, New York, NY',
            'price_range': '$$',
            'dining_style': 'CAFE',
            'location_region': 'New York',
            'latitude': 40.7250,
            'longitude': -73.9990,
            'features': ['COFFEE', 'WIFI', 'QUIET'],
            'types': ['cafe', 'coffee', 'bookstore']
        },
        {
            'name': 'Tequila & Tacos',
            'address': '777 10th Ave, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7600,
            'longitude': -73.9930,
            'features': ['ALCOHOL', 'LATE', 'SPICY'],
            'types': ['mexican', 'taco', 'bar', 'restaurant']
        },
        {
            'name': 'Ice Cream Palace',
            'address': '222 W 14th St, New York, NY',
            'price_range': '$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7380,
            'longitude': -74.0010,
            'features': ['DESSERT', 'FAMILY', 'TAKEOUT'],
            'types': ['ice_cream', 'dessert', 'sweet']
        },
        {
            'name': 'Dim Sum Garden',
            'address': '888 Canal St, New York, NY',
            'price_range': '$$',
            'dining_style': 'CASUAL',
            'location_region': 'New York',
            'latitude': 40.7170,
            'longitude': -74.0000,
            'features': ['FAMILY', 'AUTHENTIC'],
            'types': ['chinese', 'dim_sum', 'asian', 'restaurant']
        }
    ]
    
    # Combine original and additional restaurants
    all_restaurants = restaurants + additional_restaurants
    
    # Create establishments
    for restaurant_data in all_restaurants:
        features = restaurant_data.pop('features', [])
        types = restaurant_data.pop('types', [])
        
        # Add place_id if not present (for Google Maps integration)
        if 'place_id' not in restaurant_data:
            restaurant_data['place_id'] = f"sample_{random.randint(1000, 9999)}"
            
        # Add rating if not present
        if 'rating' not in restaurant_data:
            restaurant_data['rating'] = round(random.uniform(3.0, 5.0), 1)
            
        # Check if establishment already exists
        if not Establishment.objects.filter(name=restaurant_data['name'], user=user).exists():
            # Create establishment
            establishment = Establishment.objects.create(
                user=user,
                **restaurant_data
            )
            
            # Add features
            for feature_type in features:
                EstablishmentFeature.objects.create(
                    establishment=establishment,
                    feature_type=feature_type
                )
                
            # Add types as a JSON field
            establishment.types = types
            establishment.save()
                
            print(f"Created establishment: {establishment.name}")
        else:
            print(f"Establishment already exists: {restaurant_data['name']}")

def add_sample_establishments_with_geometry(user):
    """Add sample establishments with proper geometry for location-based features"""
    
    establishments_with_geometry = [
        {
            'name': 'Central Park Cafe',
            'vicinity': 'Central Park, New York, NY',
            'formatted_address': 'Central Park, New York, NY 10022',
            'price_level': 2,
            'rating': 4.5,
            'diningStyle': 'CAFE',
            'geometry': {
                'location': {
                    'lat': 40.7812,
                    'lng': -73.9665
                }
            },
            'place_id': 'sample_central_park_cafe',
            'types': ['cafe', 'restaurant', 'food'],
            'specialFeatures': ['OUTDOOR', 'VEGAN', 'COFFEE']
        },
        {
            'name': 'Times Square Diner',
            'vicinity': 'Times Square, New York, NY',
            'formatted_address': '123 Broadway, New York, NY 10036',
            'price_level': 2,
            'rating': 4.0,
            'diningStyle': 'CASUAL',
            'geometry': {
                'location': {
                    'lat': 40.7580,
                    'lng': -73.9855
                }
            },
            'place_id': 'sample_times_square_diner',
            'types': ['diner', 'restaurant', 'american'],
            'specialFeatures': ['TAKEOUT', 'FAMILY', 'BREAKFAST']
        },
        {
            'name': 'Brooklyn Pizza Co.',
            'vicinity': 'Williamsburg, Brooklyn, NY',
            'formatted_address': '555 Bedford Ave, Brooklyn, NY 11211',
            'price_level': 1,
            'rating': 4.7,
            'diningStyle': 'CASUAL',
            'geometry': {
                'location': {
                    'lat': 40.7081,
                    'lng': -73.9571
                }
            },
            'place_id': 'sample_brooklyn_pizza',
            'types': ['pizza', 'restaurant', 'italian'],
            'specialFeatures': ['TAKEOUT', 'DELIVERY', 'FAMILY']
        },
        {
            'name': 'The Highline Restaurant',
            'vicinity': 'Chelsea, New York, NY',
            'formatted_address': '123 10th Ave, New York, NY 10011',
            'price_level': 3,
            'rating': 4.4,
            'diningStyle': 'FINE',
            'geometry': {
                'location': {
                    'lat': 40.7480,
                    'lng': -74.0048
                }
            },
            'place_id': 'sample_highline_restaurant',
            'types': ['fine_dining', 'restaurant', 'american'],
            'specialFeatures': ['OUTDOOR', 'RESERVATION', 'ALCOHOL']
        },
        {
            'name': 'Little Italy Trattoria',
            'vicinity': 'Little Italy, New York, NY',
            'formatted_address': '123 Mulberry St, New York, NY 10013',
            'price_level': 3,
            'rating': 4.6,
            'diningStyle': 'CASUAL',
            'geometry': {
                'location': {
                    'lat': 40.7197,
                    'lng': -73.9977
                }
            },
            'place_id': 'sample_little_italy_trattoria',
            'types': ['italian', 'restaurant', 'pasta'],
            'specialFeatures': ['AUTHENTIC', 'ALCOHOL', 'FAMILY']
        }
    ]
    
    for est_data in establishments_with_geometry:
        special_features = est_data.pop('specialFeatures', [])
        types = est_data.pop('types', [])
        
        # Check if establishment already exists by place_id
        if not Establishment.objects.filter(place_id=est_data['place_id']).exists():
            # Create establishment with all the Google Places-like data
            establishment = Establishment.objects.create(
                user=user,
                **est_data
            )
            
            # Add features
            for feature_type in special_features:
                EstablishmentFeature.objects.create(
                    establishment=establishment,
                    feature_type=feature_type
                )
                
            # Add types directly
            establishment.types = types
            establishment.save()
                
            print(f"Created establishment with geometry: {establishment.name}")
        else:
            print(f"Establishment already exists: {est_data['name']}")

if __name__ == '__main__':
    print("Adding sample establishments to database...")
    user = create_test_user()
    add_sample_establishments(user)
    add_sample_establishments_with_geometry(user)
    print("Done!") 