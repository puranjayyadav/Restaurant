# views.py
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import auth
import firebase_admin
from firebase_admin import credentials, firestore
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Establishment, EstablishmentFeature, ScrapedRestaurant, PreCreatedItinerary
from .serializers import (
    EstablishmentSerializer, EstablishmentFeatureSerializer,
    ScrapedRestaurantSerializer, ScrapedRestaurantListSerializer
)
from django.db.models import Q
from math import radians, cos, sin, asin, sqrt
from django.shortcuts import get_object_or_404
from .recommendation import RestaurantRecommender
from .utils import match_restaurant_with_postgres, enrich_restaurant_data
import uuid

# Initialize Firebase app (if not already initialized)
# Supports both environment variable (Railway) and file path (local dev)
if not firebase_admin._apps:
    import os
    import json
    
    # Try to get credentials from environment variable first (for Railway)
    firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS')
    
    print(f"DEBUG: Checking Firebase credentials...")
    print(f"DEBUG: FIREBASE_CREDENTIALS env var exists: {firebase_creds_json is not None}")
    print(f"DEBUG: FIREBASE_CREDENTIALS length: {len(firebase_creds_json) if firebase_creds_json else 0}")
    
    if firebase_creds_json:
        # Parse JSON string from environment variable
        try:
            # Handle both string and already-parsed JSON
            if isinstance(firebase_creds_json, str):
                cred_dict = json.loads(firebase_creds_json)
            else:
                cred_dict = firebase_creds_json
            
            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in cred_dict]
            if missing_fields:
                raise ValueError(f"Missing required fields in credentials: {missing_fields}")
            
            cred = credentials.Certificate(cred_dict)
            print("DEBUG: Initialized Firebase using environment variable")
            print(f"DEBUG: Firebase project_id: {cred_dict.get('project_id', 'unknown')}")
            print(f"DEBUG: Firebase client_email: {cred_dict.get('client_email', 'unknown')}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ERROR: Failed to parse FIREBASE_CREDENTIALS: {str(e)}")
            print(f"ERROR: FIREBASE_CREDENTIALS length: {len(firebase_creds_json) if firebase_creds_json else 0}")
            print(f"ERROR: First 200 chars: {firebase_creds_json[:200] if firebase_creds_json else 'None'}")
            raise ValueError(f"Invalid FIREBASE_CREDENTIALS format: {str(e)}. Please check that the environment variable contains valid JSON.")
    else:
        # Fallback to file path (for local development)
        SERVICE_ACCOUNT_PATH = '../creds/restaurant-47dab-firebase-adminsdk-fbsvc-a2225a7d82.json'
        if os.path.exists(SERVICE_ACCOUNT_PATH):
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            print("DEBUG: Initialized Firebase using file path")
        else:
            # Try alternative path
            alt_path = os.path.join(os.path.dirname(__file__), '..', '..', 'creds', 'restaurant-47dab-firebase-adminsdk-fbsvc-a2225a7d82.json')
            if os.path.exists(alt_path):
                cred = credentials.Certificate(alt_path)
                print(f"DEBUG: Initialized Firebase using alternative path: {alt_path}")
            else:
                error_msg = (
                    "FIREBASE_CREDENTIALS environment variable is not set!\n"
                    "Please set it on Railway:\n"
                    "1. Go to your Railway project dashboard\n"
                    "2. Select your Django service\n"
                    "3. Go to Variables tab\n"
                    "4. Add FIREBASE_CREDENTIALS with the JSON content from your service account file"
                )
                print(f"ERROR: {error_msg}")
                raise FileNotFoundError(error_msg)
    
    try:
        firebase_admin.initialize_app(cred)
        print("DEBUG: Firebase app initialized successfully")
    except Exception as init_error:
        print(f"ERROR: Failed to initialize Firebase app: {str(init_error)}")
        raise

# Get a Firestore client
db = firestore.client()

@api_view(['POST'])
@authentication_classes([])  # Disable DRF's token authentication for this endpoint
def verify_token(request):
    """
    Verify a Firebase ID token and return the associated user ID.
    This endpoint handles authentication from the Flutter app.
    """
    # 1. Parse the 'Authorization' header
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response({"error": "Missing Authorization header"}, 
                        status=status.HTTP_401_UNAUTHORIZED)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return Response({"error": "Invalid Authorization header format"}, 
                        status=status.HTTP_401_UNAUTHORIZED)

    id_token = parts[1]

    try:
        # 2. Verify the Firebase token directly
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get('uid', None)
        if not uid:
            return Response({"error": "No UID in token"}, status=status.HTTP_401_UNAUTHORIZED)

        # Successfully verified token, return user info
        return Response({
            "message": "Token is valid", 
            "uid": uid,
            "email": decoded_token.get('email', ''),
            "name": decoded_token.get('name', '')
        }, status=status.HTTP_200_OK)
    except auth.ExpiredIdTokenError:
        return Response({"error": "Token is expired"}, 
                        status=status.HTTP_401_UNAUTHORIZED)
    except auth.InvalidIdTokenError:
        return Response({"error": "Invalid Firebase token"}, 
                        status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({"error": f"Token verification failed: {str(e)}"}, 
                        status=status.HTTP_401_UNAUTHORIZED)
    

    
@api_view(['GET'])
def get_trips(request):
    # 1. Extract the Firebase ID token from the Authorization header.
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response({"error": "Missing Authorization header"}, status=status.HTTP_401_UNAUTHORIZED)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return Response({"error": "Invalid Authorization header format"}, status=status.HTTP_401_UNAUTHORIZED)

    id_token = parts[1]

    try:
        # 2. Verify the token and extract the UID.
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get('uid')
        if not uid:
            return Response({"error": "UID not found in token"}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    # 3. Query Firestore for trips that match this UID.
    db = firestore.client()
    try:
        # Query the "trips" collection for documents where 'uid' equals the user's UID.
        trips_query = db.collection('trips').where('uid', '==', uid).order_by('date', direction=firestore.Query.DESCENDING).get()
        trips = [doc.to_dict() for doc in trips_query]
        return Response({"trips": trips}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EstablishmentViewSet(viewsets.ModelViewSet):
    serializer_class = EstablishmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['price_range', 'dining_style', 'location_region']
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'created_at', 'updated_at']

    def get_queryset(self):
        queryset = Establishment.objects.filter(user=self.request.user)
        
        # Filter by features
        features = self.request.query_params.getlist('features', [])
        if features:
            queryset = queryset.filter(features__feature_type__in=features).distinct()
        
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_available_filters(self):
        """Return available filter options for the frontend"""
        return {
            'price_ranges': dict(Establishment.PRICE_RANGES),
            'dining_styles': dict(Establishment.DINING_STYLES),
            'features': dict(EstablishmentFeature.FEATURE_TYPES),
            'locations': list(Establishment.objects.filter(
                user=self.request.user
            ).values_list('location_region', flat=True).distinct())
        }

@api_view(['GET'])
@permission_classes([])

def get_trip_recommendations(request, trip_id):
    """Get personalized restaurant recommendations for a trip.
    
    This endpoint uses the ML-based recommendation engine to suggest
    restaurants based on user preferences and trip location.
    """
    try:
        # Get Firebase token from authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response({"error": "Missing Authorization header"}, 
                            status=status.HTTP_401_UNAUTHORIZED)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return Response({"error": "Invalid Authorization header format"}, 
                            status=status.HTTP_401_UNAUTHORIZED)

        id_token = parts[1]
        
        # Verify token and get user ID
        try:
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token.get('uid')
        except Exception as e:
            return Response({"error": f"Invalid token: {str(e)}"}, 
                            status=status.HTTP_401_UNAUTHORIZED)
        
        # Get trip from Firebase
        db = firestore.client()
        trip_doc = db.collection('trips').document(trip_id).get()
        
        if not trip_doc.exists:
            return Response(
                {"error": "Trip not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        trip_data = trip_doc.to_dict()
        
        # Check if this trip belongs to the authenticated user
        if trip_data.get('uid') != uid:
            return Response(
                {"error": "You don't have permission to access this trip"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get trip location (end address as an example)
        trip_location = trip_data.get('endAddress', '')
        
        if not trip_location:
            return Response(
                {"error": "Trip has no location information"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Convert Firebase user ID to Django user ID
        # This assumes your Django user IDs match Firebase UIDs or you have a mapping
        user_id = request.user.id
        
        # Initialize and use recommender
        recommender = RestaurantRecommender()
        
        # Get recommendations
        recommendations = recommender.recommend_for_trip(user_id, trip_location)
        
        serializer = EstablishmentSerializer(recommendations, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {"error": f"Failed to get recommendations: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_similar_restaurants(request, establishment_id):
    """Get restaurants similar to the specified establishment.
    
    This endpoint uses content-based filtering to find restaurants
    with similar characteristics to the one specified.
    """
    try:
        # Check if the establishment exists and user has access
        establishment = get_object_or_404(Establishment, id=establishment_id)
        
        # Initialize recommender
        recommender = RestaurantRecommender()
        
        # Get recommendations (similar restaurants)
        similar_restaurants = recommender.recommend_similar_restaurants(establishment_id)
        
        serializer = EstablishmentSerializer(similar_restaurants, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {"error": f"Failed to get similar restaurants: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_user_interaction(request):
    """Record user interaction with a restaurant to improve recommendations.
    
    This endpoint allows tracking various user interactions like viewing,
    saving, or rating restaurants to build a better recommendation model.
    """
    try:
        # Get required data from request
        establishment_id = request.data.get('establishment_id')
        interaction_type = request.data.get('interaction_type')
        rating = request.data.get('rating', None)
        trip_id = request.data.get('trip_id', None)
        
        # Validate input
        if not establishment_id or not interaction_type:
            return Response(
                {"error": "Missing required fields"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate interaction type
        valid_types = ['VIEW', 'SAVE', 'VISIT', 'RATE']
        if interaction_type not in valid_types:
            return Response(
                {"error": f"Invalid interaction type. Must be one of: {', '.join(valid_types)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get establishment
        establishment = get_object_or_404(Establishment, id=establishment_id)
        
        # Create UserInteraction instance
        from .models import UserInteraction
        
        interaction = UserInteraction(
            user=request.user,
            establishment=establishment,
            interaction_type=interaction_type,
            rating=rating if interaction_type == 'RATE' else None,
            trip_id=trip_id  # Use trip_id directly instead of the trip object
        )
        
        # Save the interaction
        interaction.save()
        
        return Response({
            "success": True, 
            "message": "Interaction recorded",
            "interaction_id": interaction.id
        })
    except ValueError as ve:
        return Response(
            {"error": str(ve)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to record interaction: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@authentication_classes([])  # Disable DRF's authentication for this endpoint
def create_session(request):
    """Create a new session for a user.
    
    Receives a userId from the request and returns a unique sessionId
    that can be used to track the user's session.
    """
    user_id = request.data.get('userId')
    if not user_id:
        return Response({"error": "Missing userId"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # You could store this session in your database if needed
    # For now, just return the generated ID
    
    return Response({"sessionId": session_id}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([])  # Disable authentication requirement completely
def get_personalized_recommendations(request):
    """Get personalized restaurant recommendations based on user's activity history.
    
    This endpoint analyzes user interactions and preferences to provide
    tailored restaurant recommendations for the discovery radar.
    """
    try:
        # Skip authentication for debugging
        # Use a fixed user ID for testing
        user_id = 1  
        
        # Print debug information
        print(f"DEBUG: Received recommendation request with params: {request.query_params}")
        
        # Initialize recommender
        recommender = RestaurantRecommender()
        
        # Get location from query params if available
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        location_filter = request.query_params.get('location', '')
        
        print(f"DEBUG: Location parameters - lat: {lat}, lon: {lon}, location_filter: {location_filter}")
        
        # If a location is provided, filter by it
        if location_filter:
            print(f"DEBUG: Using location filter: {location_filter}")
            recommendations = recommender.recommend_for_trip(user_id, location_filter)
        # If lat/lon coordinates are provided
        elif lat and lon:
            print(f"DEBUG: Using coordinates: {lat}, {lon}")
            # Use the new specialized method for coordinates-based recommendations
            recommendations = recommender.recommend_by_coordinates(
                user_id, 
                lat, 
                lon, 
                radius_km=5,  # Default 5km radius
                n=5  # Return top 5 recommendations
            )
        else:
            print("DEBUG: No location specified, using general recommendations")
            # No location filter provided, get general recommendations
            all_establishments = Establishment.objects.all()
            
            if not all_establishments:
                print("DEBUG: No establishments found in database")
                recommendations = []
            else:        
                print(f"DEBUG: Found {all_establishments.count()} establishments for recommendations")
                # Get user preferences vector
                user_vector = recommender.get_user_vector(user_id)
                
                # Calculate recommendations
                establishment_scores = []
                for est in all_establishments:
                    est_vector = recommender.get_establishment_vector(est)
                    similarity = recommender.cosine_similarity(user_vector, est_vector)
                    establishment_scores.append((est, similarity))
                    
                # Sort by similarity and get top 5
                establishment_scores.sort(key=lambda x: x[1], reverse=True)
                recommendations = [est for est, score in establishment_scores[:5]]
        
        print(f"DEBUG: Returning {len(recommendations)} recommendations")
        serializer = EstablishmentSerializer(recommendations, many=True)
        return Response(serializer.data)
    except Exception as e:
        import traceback
        print(f"DEBUG: Error in recommendation API: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to get recommendations: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])
def generate_day_itinerary(request):
    """
    Generate a day itinerary from morning to evening based on user location and selected categories.
    Ensures all places are within max_distance_km of each other (default 1.5km).
    """
    import math
    import json
    
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        
        user_id = data.get('user_id')
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        selected_categories = data.get('selected_categories', [])
        max_distance_km = float(data.get('max_distance_km', 3.0))  # Increased from 1.5 to 3.0 for rural areas
        places_data = data.get('places', [])  # Places fetched from Google API by Flutter
        vegetarian_filter = data.get('vegetarian_filter', False)  # Vegetarian filter option
        
        print(f"DEBUG: Using max distance: {max_distance_km}km between places")
        
        if not places_data:
            return Response(
                {"error": "No places provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Category to Google Places type mapping
        category_to_types = {
            'restaurants': ['restaurant', 'food', 'meal_takeaway'],
            'cafes': ['cafe', 'bakery'],
            'museums': ['museum', 'art_gallery'],
            'parks': ['park'],
            'shopping': ['shopping_mall', 'store'],
            'bars': ['bar', 'night_club', 'lounge'],
            'dessert': ['bakery', 'cafe']
        }
        
        # Build allowed types from selected categories
        allowed_types_set = set()
        for category in selected_categories:
            if category.lower() in category_to_types:
                allowed_types_set.update(category_to_types[category.lower()])
        
        # Dynamically build time slots based on selected categories
        time_slots = []
        
        # Morning slot - prioritize cafes, bakeries, breakfast places
        morning_types = []
        if any(cat.lower() in ['cafes', 'dessert'] for cat in selected_categories):
            morning_types.extend(['cafe', 'bakery'])
        if any(cat.lower() == 'restaurants' for cat in selected_categories):
            morning_types.extend(['breakfast', 'restaurant'])  # Breakfast restaurants
        if morning_types:
            time_slots.append({
                'name': 'morning',
                'start_time': '09:00',
                'end_time': '11:00',
                'allowed_types': morning_types,
                'max_places': 2
            })
        
        # Mid-day slot - prioritize restaurants
        midday_types = []
        if any(cat.lower() == 'restaurants' for cat in selected_categories):
            midday_types.extend(['restaurant', 'food', 'meal_takeaway'])
        if any(cat.lower() == 'cafes' for cat in selected_categories):
            midday_types.extend(['cafe'])
        if midday_types:
            time_slots.append({
                'name': 'mid_day',
                'start_time': '11:00',
                'end_time': '14:00',
                'allowed_types': midday_types,
                'max_places': 2
            })
        
        # Afternoon slot - prioritize museums, parks, cafes (only if selected)
        afternoon_types = []
        if any(cat.lower() == 'museums' for cat in selected_categories):
            afternoon_types.extend(['museum', 'art_gallery', 'library'])
        if any(cat.lower() == 'parks' for cat in selected_categories):
            afternoon_types.append('park')
        if any(cat.lower() == 'cafes' for cat in selected_categories):
            afternoon_types.append('cafe')
        if any(cat.lower() == 'shopping' for cat in selected_categories):
            afternoon_types.extend(['shopping_mall', 'store'])
        # If no specific afternoon categories, allow restaurants/cafes
        if not afternoon_types:
            if any(cat.lower() == 'restaurants' for cat in selected_categories):
                afternoon_types.extend(['restaurant', 'cafe'])
            elif any(cat.lower() == 'cafes' for cat in selected_categories):
                afternoon_types.append('cafe')
        if afternoon_types:
            time_slots.append({
                'name': 'afternoon',
                'start_time': '14:00',
                'end_time': '17:00',
                'allowed_types': afternoon_types,
                'max_places': 2
            })
        
        # Evening slot - prioritize restaurants and bars
        evening_types = []
        if any(cat.lower() == 'restaurants' for cat in selected_categories):
            evening_types.extend(['restaurant', 'food'])
        if any(cat.lower() == 'bars' for cat in selected_categories):
            evening_types.extend(['bar', 'night_club', 'lounge'])
        if any(cat.lower() == 'dessert' for cat in selected_categories):
            evening_types.extend(['bakery', 'cafe'])
        if evening_types:
            time_slots.append({
                'name': 'evening',
                'start_time': '17:00',
                'end_time': '20:00',
                'allowed_types': evening_types,
                'max_places': 2
            })
        
        # If no time slots were created (shouldn't happen, but safety check)
        if not time_slots:
            # Fallback: create a single slot with all selected types
            fallback_types = list(allowed_types_set)
            if fallback_types:
                time_slots.append({
                    'name': 'all_day',
                    'start_time': '09:00',
                    'end_time': '20:00',
                    'allowed_types': fallback_types,
                    'max_places': 4
                })
        
        print(f"DEBUG: Selected categories: {selected_categories}")
        print(f"DEBUG: Created {len(time_slots)} time slots based on selected categories:")
        for slot in time_slots:
            print(f"  - {slot['name']}: {slot['allowed_types']}")
        
        # Filter places by selected categories (using allowed_types_set built above)
        filtered_places = []
        if selected_categories and allowed_types_set:
            for place in places_data:
                place_types = [t.lower() for t in place.get('types', [])]
                if any(t in allowed_types_set for t in place_types):
                    filtered_places.append(place)
        else:
            filtered_places = places_data
        
        # Apply vegetarian filter if enabled
        if vegetarian_filter:
            vegetarian_keywords = ['vegetarian', 'vegan', 'plant-based', 'veggie']
            vegetarian_filtered = []
            for place in filtered_places:
                # Check place name, description, or tags for vegetarian keywords
                place_name = place.get('name', '').lower()
                place_description = place.get('description', '').lower()
                place_tags = [tag.lower() for tag in place.get('tags', [])]
                place_types = [t.lower() for t in place.get('types', [])]
                
                # Combine all text fields to search
                all_text = ' '.join([place_name, place_description] + place_tags + place_types)
                
                # Check if any vegetarian keyword is present
                if any(keyword in all_text for keyword in vegetarian_keywords):
                    vegetarian_filtered.append(place)
            
            filtered_places = vegetarian_filtered
            print(f"DEBUG: After vegetarian filter: {len(filtered_places)} places remaining")
        
        # Haversine distance calculation
        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) ** 2 +
                 math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
            c = 2 * math.asin(math.sqrt(a))
            return R * c
        
        # Get place coordinates
        def get_place_coords(place):
            geometry = place.get('geometry', {})
            location = geometry.get('location', {})
            return (location.get('lat'), location.get('lng'))
        
        # Generate itinerary
        itinerary = []
        last_location = (latitude, longitude)
        used_place_ids = set()
        
        for slot in time_slots:
            slot_places = []
            
            # Find places matching this slot's types
            for place in filtered_places:
                place_id = place.get('place_id') or place.get('id')
                if place_id in used_place_ids:
                    continue
                
                place_types = [t.lower() for t in place.get('types', [])]
                if any(t in slot['allowed_types'] for t in place_types):
                    coords = get_place_coords(place)
                    if coords[0] and coords[1]:
                        distance = calculate_distance(
                            last_location[0], last_location[1],
                            coords[0], coords[1]
                        )
                        # For first slot, allow larger radius to find initial places
                        max_dist = max_distance_km * 2 if slot == time_slots[0] else max_distance_km
                        if distance <= max_dist:
                            slot_places.append({
                                'place': place,
                                'distance': distance,
                                'coords': coords
                            })
            
            # Add variety: shuffle places within distance tiers for randomization
            # Tier 1: Very close (0-500m) - highest priority
            # Tier 2: Walkable (500m-1km) - medium priority  
            # Tier 3: Further (1km-1.5km) - lower priority
            import random
            
            tier1 = [p for p in slot_places if p['distance'] <= 0.5]
            tier2 = [p for p in slot_places if 0.5 < p['distance'] <= 1.0]
            tier3 = [p for p in slot_places if 1.0 < p['distance'] <= max_distance_km]
            
            # Shuffle within each tier for variety
            random.shuffle(tier1)
            random.shuffle(tier2)
            random.shuffle(tier3)
            
            # Combine tiers with preference for closer places
            sorted_places = tier1 + tier2 + tier3
            selected = sorted_places[:slot['max_places']]
            
            for item in selected:
                place = item['place']
                place_id = place.get('place_id') or place.get('id')
                used_place_ids.add(place_id)
                
                distance_km = item['distance']
                walk_time_minutes = int((distance_km / 5.0) * 60)  # 5 km/h walking speed
                
                itinerary_item = {
                    'slot_name': slot['name'],
                    'start_time': slot['start_time'],
                    'place_name': place.get('name', 'Unknown'),
                    'place_id': place_id,
                    'latitude': item['coords'][0],
                    'longitude': item['coords'][1],
                    'address': place.get('vicinity', place.get('formatted_address', 'Address not available')),
                    'distance_from_previous': round(distance_km, 2),
                    'estimated_walk_time': walk_time_minutes,
                    'types': place.get('types', []),
                    'photos': place.get('photos', [])  # Include photos
                }
                itinerary.append(itinerary_item)
                last_location = item['coords']
        
        return Response({
            'itinerary': itinerary,
            'total_items': len(itinerary),
            'neighborhood': 'Local Area'  # Could be extracted from address
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error generating itinerary: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to generate itinerary: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])
def generate_and_enrich_itinerary(request):
    """
    Generate a day itinerary with Postgres enrichment.
    
    Accepts places from frontend (fetched via Google Places API) and enriches
    them with data from Postgres database when matches are found.
    
    Query params:
    - cuisine: Cuisine type filter (e.g., "Italian", "French")
    - price_range: Price range filter (e.g., "$30 and under", "$31-$50", "$50+")
    - min_rating: Minimum rating (0-5)
    - tags: Comma-separated tags (e.g., "Neighborhood gem,Charming")
    - latitude: User latitude
    - longitude: User longitude
    - radius_km: Search radius in km (1 or 3)
    - places: List of places from Google Places API (optional, if not provided will use filters)
    """
    import math
    import json
    
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        
        # Get location
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        radius_km = float(data.get('radius_km', 3.0))
        
        # Get filters
        cuisine = data.get('cuisine', '').strip()
        price_range = data.get('price_range', '').strip()
        min_rating = float(data.get('min_rating', 0))
        tags_str = data.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
        
        # Get places from frontend (already fetched via Google Places API)
        places_data = data.get('places', [])
        
        # If no places provided, return error (frontend should fetch places first)
        if not places_data:
            return Response(
                {"error": "No places provided. Please fetch places from Google Places API first."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filter places based on criteria
        filtered_places = []
        for place in places_data:
            # Filter by rating
            place_rating = place.get('rating', 0)
            if place_rating < min_rating:
                continue
            
            # Filter by price level (Google Places uses 0-4)
            if price_range:
                place_price_level = place.get('price_level', -1)
                price_mapping = {
                    '$30 and under': [0, 1],  # $ and $$
                    '$31-$50': [2],  # $$$
                    '$50+': [3, 4]  # $$$$ and above
                }
                if price_range in price_mapping:
                    if place_price_level not in price_mapping[price_range]:
                        continue
            
            # Filter by cuisine (check types and name)
            if cuisine:
                place_types = [t.lower() for t in place.get('types', [])]
                place_name = place.get('name', '').lower()
                cuisine_lower = cuisine.lower()
                
                # Check if cuisine matches any type or name
                cuisine_match = (
                    cuisine_lower in place_name or
                    any(cuisine_lower in t for t in place_types) or
                    any(t in ['restaurant', 'food', 'meal_takeaway'] for t in place_types)
                )
                if not cuisine_match:
                    continue
            
            # Filter by tags (check in name, types, or description)
            if tags:
                place_name = place.get('name', '').lower()
                place_types = [t.lower() for t in place.get('types', [])]
                place_description = place.get('description', '').lower() if place.get('description') else ''
                
                # Check if any tag matches
                tag_match = False
                for tag in tags:
                    tag_lower = tag.lower()
                    if (tag_lower in place_name or 
                        any(tag_lower in t for t in place_types) or
                        tag_lower in place_description):
                        tag_match = True
                        break
                
                if not tag_match:
                    continue
            
            # Check radius (if place has coordinates)
            geometry = place.get('geometry', {})
            location = geometry.get('location', {})
            place_lat = location.get('lat')
            place_lng = location.get('lng')
            
            if place_lat and place_lng:
                # Calculate distance
                R = 6371  # Earth radius in km
                lat1_rad = math.radians(latitude)
                lat2_rad = math.radians(place_lat)
                delta_lat = math.radians(place_lat - latitude)
                delta_lon = math.radians(place_lng - longitude)
                
                a = (math.sin(delta_lat / 2) ** 2 +
                     math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
                c = 2 * math.asin(math.sqrt(a))
                distance_km = R * c
                
                if distance_km <= radius_km:
                    filtered_places.append(place)
        
        if not filtered_places:
            return Response(
                {"error": "No places found matching the criteria"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate itinerary using existing logic
        # Reuse generate_day_itinerary core logic
        selected_categories = ['restaurants']  # Default to restaurants for discovery
        max_distance_km = radius_km
        
        # Haversine distance calculation
        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371  # Earth radius in km
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lon = math.radians(lon2 - lon1)
            
            a = (math.sin(delta_lat / 2) ** 2 +
                 math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
            c = 2 * math.asin(math.sqrt(a))
            return R * c
        
        # Get place coordinates
        def get_place_coords(place):
            geometry = place.get('geometry', {})
            location = geometry.get('location', {})
            return (location.get('lat'), location.get('lng'))
        
        # Create time slots for itinerary
        time_slots = [
            {
                'name': 'morning',
                'start_time': '09:00',
                'end_time': '11:00',
                'allowed_types': ['cafe', 'bakery', 'restaurant'],
                'max_places': 2
            },
            {
                'name': 'mid_day',
                'start_time': '11:00',
                'end_time': '14:00',
                'allowed_types': ['restaurant', 'food', 'meal_takeaway'],
                'max_places': 2
            },
            {
                'name': 'afternoon',
                'start_time': '14:00',
                'end_time': '17:00',
                'allowed_types': ['restaurant', 'cafe'],
                'max_places': 2
            },
            {
                'name': 'evening',
                'start_time': '17:00',
                'end_time': '20:00',
                'allowed_types': ['restaurant', 'food'],
                'max_places': 2
            }
        ]
        
        # Generate itinerary
        itinerary_items = []
        last_location = (latitude, longitude)
        used_place_ids = set()
        
        import random
        
        for slot in time_slots:
            slot_places = []
            
            # Find places matching this slot's types
            for place in filtered_places:
                place_id = place.get('place_id') or place.get('id')
                if place_id in used_place_ids:
                    continue
                
                place_types = [t.lower() for t in place.get('types', [])]
                if any(t in slot['allowed_types'] for t in place_types):
                    coords = get_place_coords(place)
                    if coords[0] and coords[1]:
                        distance = calculate_distance(
                            last_location[0], last_location[1],
                            coords[0], coords[1]
                        )
                        max_dist = max_distance_km * 2 if slot == time_slots[0] else max_distance_km
                        if distance <= max_dist:
                            slot_places.append({
                                'place': place,
                                'distance': distance,
                                'coords': coords
                            })
            
            # Sort by distance and select
            tier1 = [p for p in slot_places if p['distance'] <= 0.5]
            tier2 = [p for p in slot_places if 0.5 < p['distance'] <= 1.0]
            tier3 = [p for p in slot_places if 1.0 < p['distance'] <= max_distance_km]
            
            random.shuffle(tier1)
            random.shuffle(tier2)
            random.shuffle(tier3)
            
            sorted_places = tier1 + tier2 + tier3
            selected = sorted_places[:slot['max_places']]
            
            for item in selected:
                place = item['place']
                place_id = place.get('place_id') or place.get('id')
                used_place_ids.add(place_id)
                
                distance_km = item['distance']
                walk_time_minutes = int((distance_km / 5.0) * 60)  # 5 km/h walking speed
                
                itinerary_item = {
                    'slot_name': slot['name'],
                    'start_time': slot['start_time'],
                    'place_name': place.get('name', 'Unknown'),
                    'place_id': place_id,
                    'latitude': item['coords'][0],
                    'longitude': item['coords'][1],
                    'address': place.get('vicinity', place.get('formatted_address', 'Address not available')),
                    'distance_from_previous': round(distance_km, 2),
                    'estimated_walk_time': walk_time_minutes,
                    'types': place.get('types', []),
                    'photos': place.get('photos', []),
                    'rating': place.get('rating', 0),
                    'price_level': place.get('price_level', -1)
                }
                itinerary_items.append(itinerary_item)
                last_location = item['coords']
        
        # Enrich each restaurant with Postgres data
        enriched_itinerary = []
        enrichment_stats = {
            'total_restaurants': len(itinerary_items),
            'enriched_count': 0,
            'enrichment_percentage': 0
        }
        
        for item in itinerary_items:
            # Reconstruct place data from itinerary item
            place_data = {
                'name': item.get('place_name'),
                'geometry': {
                    'location': {
                        'lat': item.get('latitude'),
                        'lng': item.get('longitude')
                    }
                },
                'place_id': item.get('place_id'),
                'address': item.get('address'),
                'types': item.get('types', []),
                'photos': item.get('photos', []),
                'rating': item.get('rating', 0)
            }
            
            # Try to match with Postgres
            postgres_match = match_restaurant_with_postgres(place_data)
            
            # Enrich if match found
            if postgres_match:
                enriched_place = enrich_restaurant_data(place_data, postgres_match)
                item['is_enriched'] = True
                item['postgres_data'] = enriched_place.get('postgres_data', {})
                item['enrichment_metadata'] = enriched_place.get('enrichment_metadata', {})
                enrichment_stats['enriched_count'] += 1
            else:
                item['is_enriched'] = False
                item['postgres_data'] = {}
                item['enrichment_metadata'] = {}
            
            enriched_itinerary.append(item)
        
        # Calculate enrichment percentage
        if enrichment_stats['total_restaurants'] > 0:
            enrichment_stats['enrichment_percentage'] = round(
                (enrichment_stats['enriched_count'] / enrichment_stats['total_restaurants']) * 100, 
                1
            )
        
        return Response({
            'itinerary': enriched_itinerary,
            'total_items': len(enriched_itinerary),
            'enrichment_stats': enrichment_stats,
            'filters_applied': {
                'cuisine': cuisine,
                'price_range': price_range,
                'min_rating': min_rating,
                'tags': tags,
                'radius_km': radius_km
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error generating enriched itinerary: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to generate enriched itinerary: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ============================================================================
# Public Itinerary Sharing Feature
# ============================================================================

@api_view(['POST'])
@permission_classes([])
def submit_public_itinerary(request):
    """
    Submit an itinerary to the public feed.
    Creates a public itinerary with status='pending' in Firestore.
    """
    import json
    from datetime import datetime
    
    try:
        print(f"DEBUG: Received submit itinerary request")
        print(f"DEBUG: Content-Type: {request.content_type}")
        print(f"DEBUG: Content-Length: {request.META.get('CONTENT_LENGTH', 'unknown')}")
        
        # Parse request body - DRF's request.data already handles JSON parsing
        if hasattr(request, 'data') and request.data:
            data = request.data
        else:
            # Fallback to manual parsing
            try:
                body_str = request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body
                data = json.loads(body_str)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"DEBUG: Failed to parse request body: {str(e)}")
                return Response(
                    {"error": f"Invalid JSON in request body: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        print(f"DEBUG: Parsed data successfully")
        print(f"DEBUG: Items count: {len(data.get('items', []))}")
        print(f"DEBUG: First item sample: {str(data.get('items', [])[:1]) if data.get('items') else 'No items'}")
        
        user_id = data.get('user_id')
        user_name = data.get('user_name', 'Anonymous')
        user_photo_url = data.get('user_photo_url')
        title = data.get('title')
        description = data.get('description')
        location = data.get('location')
        
        # Handle latitude/longitude with defaults
        try:
            latitude = float(data.get('latitude', 0.0))
        except (ValueError, TypeError):
            latitude = 0.0
        
        try:
            longitude = float(data.get('longitude', 0.0))
        except (ValueError, TypeError):
            longitude = 0.0
        
        neighborhood = data.get('neighborhood', 'Local area')
        categories = data.get('categories', [])
        items = data.get('items', [])
        
        if not all([user_id, title, description, location]):
            return Response(
                {"error": "Missing required fields: user_id, title, description, location"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create document in Firestore
        # Ensure all data is JSON-serializable
        itinerary_data = {
            'user_id': str(user_id),
            'user_name': str(user_name),
            'user_photo_url': str(user_photo_url) if user_photo_url else None,
            'title': str(title),
            'description': str(description),
            'location': str(location),
            'latitude': float(latitude),
            'longitude': float(longitude),
            'neighborhood': str(neighborhood),
            'categories': list(categories) if categories else [],
            'items': items if isinstance(items, list) else [],
            'status': 'pending',
            'likes_count': 0,
            'shares_count': 0,
            'added_to_schedule_count': 0,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        # Validate data size to prevent timeouts
        import json
        data_size = len(json.dumps(itinerary_data, default=str))
        print(f"DEBUG: Itinerary data size: {data_size} bytes ({data_size / 1024:.2f} KB)")
        if data_size > 1_000_000:  # 1MB limit
            return Response(
                {"error": "Itinerary data too large. Please reduce the number of items."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f"DEBUG: Attempting to add document to Firestore...")
        import time
        import threading
        start_time = time.time()
        
        try:
            # Firestore add() returns a tuple (timestamp, DocumentReference)
            timestamp, doc_ref = db.collection('public_itineraries').add(itinerary_data)
            itinerary_id = doc_ref.id
            elapsed = time.time() - start_time
            print(f"DEBUG: Successfully created document with ID: {itinerary_id} in {elapsed:.2f}s")
        except Exception as firestore_error:
            print(f"DEBUG: Firestore error: {str(firestore_error)}")
            import traceback
            print(f"DEBUG: Firestore traceback: {traceback.format_exc()}")
            raise firestore_error
        
        # Update user stats in background thread (truly non-blocking)
        def update_user_stats_async():
            try:
                user_stats_ref = db.collection('user_stats').document(user_id)
                user_stats_doc = user_stats_ref.get()
                
                if user_stats_doc.exists:
                    user_stats_ref.update({
                        'total_public_itineraries': firestore.Increment(1),
                        'updated_at': firestore.SERVER_TIMESTAMP,
                    })
                else:
                    user_stats_ref.set({
                        'user_id': user_id,
                        'total_public_itineraries': 1,
                        'total_likes_received': 0,
                        'profile_photo_url': user_photo_url,
                        'updated_at': firestore.SERVER_TIMESTAMP,
                    })
                print(f"DEBUG: User stats updated successfully for {user_id}")
            except Exception as stats_error:
                # Don't fail the request if stats update fails
                print(f"WARNING: Failed to update user stats (non-critical): {str(stats_error)}")
        
        # Start stats update in background thread
        stats_thread = threading.Thread(target=update_user_stats_async, daemon=True)
        stats_thread.start()
        
        return Response({
            'itinerary_id': itinerary_id,
            'status': 'pending',
            'message': 'Itinerary submitted successfully. Awaiting approval.'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"DEBUG: Error submitting public itinerary: {str(e)}")
        print(f"DEBUG: {error_trace}")
        # Return detailed error for debugging
        return Response(
            {
                "error": f"Failed to submit itinerary: {str(e)}",
                "details": error_trace.split('\n')[-5:] if len(error_trace) > 0 else []
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([])
def get_public_itineraries(request):
    """
    Get public itineraries with optional filtering and sorting.
    Query params: location, categories (comma-separated), sort (likes/recent), limit, offset
    """
    try:
        import time
        location = request.query_params.get('location', '').strip()
        categories_str = request.query_params.get('categories', '')
        categories = [c.strip() for c in categories_str.split(',') if c.strip()] if categories_str else []
        sort_by = request.query_params.get('sort', 'recent')  # 'likes' or 'recent'
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        # Build query with a reasonable limit to avoid fetching everything
        # Fetch more than needed to account for filtering, but cap at 500
        max_fetch = min(500, (offset + limit) * 3)  # Fetch 3x what we need, max 500
        query = db.collection('public_itineraries').where('status', '==', 'approved')
        
        # Order by created_at for consistent pagination (if sorting by recent)
        # Note: This requires a composite index on (status, created_at)
        # If index doesn't exist, we'll sort in memory instead
        use_firestore_order = False
        if sort_by == 'recent':
            try:
                query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
                use_firestore_order = True
            except Exception as order_error:
                print(f"DEBUG: Could not add order_by to query: {str(order_error)}")
                print(f"DEBUG: Will sort in memory instead")
        
        query = query.limit(max_fetch)
        
        # Execute query with timeout
        start_time = time.time()
        try:
            docs = list(query.stream())  # Convert to list to avoid streaming issues
        except Exception as query_error:
            # If query fails (e.g., missing index), try without order_by
            if use_firestore_order and 'index' in str(query_error).lower():
                print(f"DEBUG: Query failed due to missing index, retrying without order_by: {str(query_error)}")
                query = db.collection('public_itineraries').where('status', '==', 'approved').limit(max_fetch)
                docs = list(query.stream())
                use_firestore_order = False
            else:
                raise
        print(f"DEBUG: Fetched {len(docs)} documents in {time.time() - start_time:.2f} seconds")
        
        # Helper function to serialize Firestore Timestamps
        def serialize_timestamp(ts):
            """Convert Firestore Timestamp to ISO format string or timestamp"""
            if ts is None:
                return None
            if hasattr(ts, 'timestamp'):  # Firestore Timestamp
                return ts.timestamp()
            if hasattr(ts, 'isoformat'):  # datetime
                return ts.isoformat()
            return str(ts)
        
        # Convert to list and filter
        itineraries = []
        user_ids = set()  # Collect unique user IDs for batch fetching
        
        for doc in docs:
            try:
                data = doc.to_dict()
                data['id'] = doc.id
                
                # Serialize Timestamp fields
                if 'created_at' in data:
                    data['created_at'] = serialize_timestamp(data['created_at'])
                if 'updated_at' in data:
                    data['updated_at'] = serialize_timestamp(data['updated_at'])
                
                # Filter by location
                if location:
                    if location.lower() not in data.get('location', '').lower():
                        continue
                
                # Filter by categories (if any category matches)
                if categories:
                    itinerary_categories = [c.lower() for c in data.get('categories', [])]
                    if not any(cat.lower() in itinerary_categories for cat in categories):
                        continue
                
                user_ids.add(data.get('user_id'))
                itineraries.append(data)
            except Exception as doc_error:
                print(f"DEBUG: Error processing document {doc.id}: {str(doc_error)}")
                continue
        
        # Batch fetch user stats
        user_stats_map = {}
        if user_ids:
            print(f"DEBUG: Batch fetching stats for {len(user_ids)} users")
            stats_start = time.time()
            # Firestore doesn't support batch get for multiple documents easily
            # So we'll fetch them sequentially with timeout protection
            for user_id in user_ids:
                try:
                    user_stats_doc = db.collection('user_stats').document(user_id).get()
                    if user_stats_doc.exists:
                        stats = user_stats_doc.to_dict()
                        user_stats_map[user_id] = {
                            'total_public_itineraries': stats.get('total_public_itineraries', 0),
                            'total_likes_received': stats.get('total_likes_received', 0),
                        }
                    else:
                        user_stats_map[user_id] = {
                            'total_public_itineraries': 0,
                            'total_likes_received': 0,
                        }
                except Exception as stats_error:
                    print(f"DEBUG: Error fetching stats for user {user_id}: {str(stats_error)}")
                    user_stats_map[user_id] = {
                        'total_public_itineraries': 0,
                        'total_likes_received': 0,
                    }
            print(f"DEBUG: Fetched user stats in {time.time() - stats_start:.2f} seconds")
        
        # Attach user stats to itineraries
        for itinerary in itineraries:
            user_id = itinerary.get('user_id')
            itinerary['user_stats'] = user_stats_map.get(user_id, {
                'total_public_itineraries': 0,
                'total_likes_received': 0,
            })
        
        # Sort
        if sort_by == 'likes':
            itineraries.sort(key=lambda x: x.get('likes_count', 0), reverse=True)
        else:  # recent
            # Only sort in memory if Firestore didn't sort for us
            if not use_firestore_order:
                # Handle SERVER_TIMESTAMP or None values
                def get_sort_key(x):
                    created_at = x.get('created_at')
                    if created_at is None:
                        return 0  # Put None values at the end
                    # created_at should already be serialized to timestamp
                    if isinstance(created_at, (int, float)):
                        return created_at
                    return 0
                itineraries.sort(key=get_sort_key, reverse=True)
        
        # Paginate
        total = len(itineraries)
        itineraries = itineraries[offset:offset + limit]
        
        print(f"DEBUG: Returning {len(itineraries)} itineraries (total: {total}, offset: {offset}, limit: {limit})")
        
        return Response({
            'itineraries': itineraries,
            'total': total,
            'limit': limit,
            'offset': offset,
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error fetching public itineraries: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to fetch itineraries: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])
def like_public_itinerary(request, itinerary_id):
    """
    Toggle like status for a public itinerary.
    """
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        user_id = data.get('user_id')
        
        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already liked
        like_ref = db.collection('public_itineraries').document(itinerary_id).collection('likes').document(user_id)
        like_doc = like_ref.get()
        
        itinerary_ref = db.collection('public_itineraries').document(itinerary_id)
        itinerary_doc = itinerary_ref.get()
        
        if not itinerary_doc.exists:
            return Response(
                {"error": "Itinerary not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        is_liked = like_doc.exists
        
        if is_liked:
            # Unlike: remove like document
            like_ref.delete()
            # Decrement likes_count
            itinerary_ref.update({
                'likes_count': firestore.Increment(-1),
                'updated_at': firestore.SERVER_TIMESTAMP,
            })
            # Update user stats (decrement likes received for itinerary owner)
            itinerary_data = itinerary_doc.to_dict()
            owner_id = itinerary_data.get('user_id')
            if owner_id:
                db.collection('user_stats').document(owner_id).update({
                    'total_likes_received': firestore.Increment(-1),
                })
            return Response({'liked': False, 'likes_count': itinerary_data.get('likes_count', 0) - 1})
        else:
            # Like: create like document
            like_ref.set({
                'user_id': user_id,
                'liked_at': firestore.SERVER_TIMESTAMP,
            })
            # Increment likes_count
            itinerary_ref.update({
                'likes_count': firestore.Increment(1),
                'updated_at': firestore.SERVER_TIMESTAMP,
            })
            # Update user stats (increment likes received for itinerary owner)
            itinerary_data = itinerary_doc.to_dict()
            owner_id = itinerary_data.get('user_id')
            if owner_id:
                db.collection('user_stats').document(owner_id).update({
                    'total_likes_received': firestore.Increment(1),
                })
            return Response({'liked': True, 'likes_count': itinerary_data.get('likes_count', 0) + 1})
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error toggling like: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to toggle like: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])
def add_public_itinerary_to_schedule(request, itinerary_id):
    """
    Copy a public itinerary to user's saved_itineraries.
    """
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        user_id = data.get('user_id')
        
        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get public itinerary
        itinerary_ref = db.collection('public_itineraries').document(itinerary_id)
        itinerary_doc = itinerary_ref.get()
        
        if not itinerary_doc.exists:
            return Response(
                {"error": "Itinerary not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        itinerary_data = itinerary_doc.to_dict()
        
        # Create saved itinerary
        saved_itinerary_data = {
            'user_id': user_id,
            'created_at': firestore.SERVER_TIMESTAMP,
            'location': itinerary_data.get('location'),
            'neighborhood': itinerary_data.get('neighborhood'),
            'items': itinerary_data.get('items', []),
            'categories': itinerary_data.get('categories', []),
        }
        
        saved_ref = db.collection('saved_itineraries').add(saved_itinerary_data)
        
        # Increment added_to_schedule_count
        itinerary_ref.update({
            'added_to_schedule_count': firestore.Increment(1),
            'updated_at': firestore.SERVER_TIMESTAMP,
        })
        
        return Response({
            'saved_itinerary_id': saved_ref.id,
            'message': 'Itinerary added to your schedule'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error adding itinerary to schedule: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to add itinerary to schedule: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])
def share_public_itinerary(request, itinerary_id):
    """
    Increment share count for a public itinerary.
    """
    try:
        itinerary_ref = db.collection('public_itineraries').document(itinerary_id)
        itinerary_doc = itinerary_ref.get()
        
        if not itinerary_doc.exists:
            return Response(
                {"error": "Itinerary not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Increment shares_count
        itinerary_ref.update({
            'shares_count': firestore.Increment(1),
            'updated_at': firestore.SERVER_TIMESTAMP,
        })
        
        itinerary_data = itinerary_doc.to_dict()
        
        return Response({
            'shares_count': itinerary_data.get('shares_count', 0) + 1,
            'share_link': f"https://yourapp.com/itinerary/{itinerary_id}"  # Update with actual app URL
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error sharing itinerary: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to share itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([])
def update_public_itinerary(request, itinerary_id):
    """
    Update a user's own public itinerary.
    """
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        user_id = data.get('user_id')
        
        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        itinerary_ref = db.collection('public_itineraries').document(itinerary_id)
        itinerary_doc = itinerary_ref.get()
        
        if not itinerary_doc.exists:
            return Response(
                {"error": "Itinerary not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        itinerary_data = itinerary_doc.to_dict()
        
        # Check ownership
        if itinerary_data.get('user_id') != user_id:
            return Response(
                {"error": "You can only edit your own itineraries"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check status (can only edit pending or approved)
        status_val = itinerary_data.get('status')
        if status_val not in ['pending', 'approved']:
            return Response(
                {"error": "Cannot edit itinerary with current status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update allowed fields
        update_data = {
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        if 'title' in data:
            update_data['title'] = data['title']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'items' in data:
            update_data['items'] = data['items']
        if 'categories' in data:
            update_data['categories'] = data['categories']
        
        itinerary_ref.update(update_data)
        
        return Response({
            'message': 'Itinerary updated successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error updating itinerary: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to update itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['DELETE'])
@permission_classes([])
def delete_public_itinerary(request, itinerary_id):
    """
    Delete a user's own public itinerary.
    """
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        user_id = data.get('user_id')
        
        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        itinerary_ref = db.collection('public_itineraries').document(itinerary_id)
        itinerary_doc = itinerary_ref.get()
        
        if not itinerary_doc.exists:
            return Response(
                {"error": "Itinerary not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        itinerary_data = itinerary_doc.to_dict()
        
        # Check ownership
        if itinerary_data.get('user_id') != user_id:
            return Response(
                {"error": "You can only delete your own itineraries"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete all likes subcollection
        likes_ref = itinerary_ref.collection('likes')
        for like_doc in likes_ref.stream():
            like_doc.reference.delete()
        
        # Delete itinerary
        itinerary_ref.delete()
        
        # Update user stats
        db.collection('user_stats').document(user_id).update({
            'total_public_itineraries': firestore.Increment(-1),
        })
        
        return Response({
            'message': 'Itinerary deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error deleting itinerary: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to delete itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])
def approve_public_itinerary(request, itinerary_id):
    """
    Admin endpoint to approve a public itinerary.
    """
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        admin_user_id = data.get('admin_user_id')
        
        # TODO: Add admin check here
        # For now, allow any user to approve (should be restricted in production)
        
        itinerary_ref = db.collection('public_itineraries').document(itinerary_id)
        itinerary_doc = itinerary_ref.get()
        
        if not itinerary_doc.exists:
            return Response(
                {"error": "Itinerary not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        itinerary_data = itinerary_doc.to_dict()
        
        if itinerary_data.get('status') != 'pending':
            return Response(
                {"error": "Itinerary is not pending approval"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status to approved
        itinerary_ref.update({
            'status': 'approved',
            'approved_at': firestore.SERVER_TIMESTAMP,
            'approved_by': admin_user_id,
            'updated_at': firestore.SERVER_TIMESTAMP,
        })
        
        return Response({
            'message': 'Itinerary approved successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error approving itinerary: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to approve itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([])
def get_user_stats(request, user_id):
    """
    Get user statistics for public itineraries.
    """
    try:
        user_stats_ref = db.collection('user_stats').document(user_id)
        user_stats_doc = user_stats_ref.get()
        
        if user_stats_doc.exists:
            stats = user_stats_doc.to_dict()
            return Response({
                'user_id': user_id,
                'total_public_itineraries': stats.get('total_public_itineraries', 0),
                'total_likes_received': stats.get('total_likes_received', 0),
                'profile_photo_url': stats.get('profile_photo_url'),
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'user_id': user_id,
                'total_public_itineraries': 0,
                'total_likes_received': 0,
                'profile_photo_url': None,
            }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error fetching user stats: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to fetch user stats: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# Scraped Restaurant API Endpoints
# ============================================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km using Haversine formula"""
    R = 6371  # Earth radius in km
    dlat = radians(float(lat2) - float(lat1))
    dlon = radians(float(lon2) - float(lon1))
    a = sin(dlat/2)**2 + cos(radians(float(lat1))) * cos(radians(float(lat2))) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))


@api_view(['GET'])
@permission_classes([])
def get_scraped_restaurants(request):
    """
    Get scraped restaurants with filtering options:
    - city, state: Filter by location
    - latitude, longitude, radius_km: Filter by proximity
    - source: Filter by source (yelp, google, etc.)
    - min_rating: Minimum rating
    - search: Search by name
    - limit: Number of results (default 50, max 200)
    """
    try:
        # Get query parameters
        city = request.GET.get('city')
        state = request.GET.get('state')
        source = request.GET.get('source')
        min_rating = request.GET.get('min_rating')
        search = request.GET.get('search', '').strip()
        limit = min(int(request.GET.get('limit', 50)), 200)
        
        # Geospatial filtering
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        radius_km = request.GET.get('radius_km', 10)  # Default 10km radius
        
        # Start with base query
        queryset = ScrapedRestaurant.objects.filter(is_active=True, duplicate_of__isnull=True)
        
        # Apply filters
        if city:
            queryset = queryset.filter(city__icontains=city)
        if state:
            queryset = queryset.filter(state__icontains=state)
        if source:
            queryset = queryset.filter(source=source)
        if min_rating:
            queryset = queryset.filter(rating__gte=float(min_rating))
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(address__icontains=search) |
                Q(categories__icontains=search)
            )
        
        # Geospatial filtering
        if latitude and longitude:
            lat = float(latitude)
            lon = float(longitude)
            radius = float(radius_km)
            
            # Filter by approximate bounding box first (faster)
            # Rough approximation: 1 degree latitude ≈ 111 km
            lat_delta = radius / 111.0
            lon_delta = radius / (111.0 * cos(radians(lat)))
            
            queryset = queryset.filter(
                latitude__gte=lat - lat_delta,
                latitude__lte=lat + lat_delta,
                longitude__gte=lon - lon_delta,
                longitude__lte=lon + lon_delta
            )
        
        # Order by quality and rating
        queryset = queryset.order_by('-data_quality_score', '-rating', 'name')[:limit]
        
        # Calculate distances if lat/lon provided
        restaurants = list(queryset)
        if latitude and longitude:
            lat = float(latitude)
            lon = float(longitude)
            radius = float(radius_km)
            
            # Filter by exact distance and add distance field
            results = []
            for restaurant in restaurants:
                if restaurant.latitude and restaurant.longitude:
                    distance = haversine_distance(
                        lat, lon,
                        float(restaurant.latitude),
                        float(restaurant.longitude)
                    )
                    if distance <= radius:
                        restaurant.distance_km = round(distance, 2)
                        results.append(restaurant)
            restaurants = results
            # Re-sort by distance
            restaurants.sort(key=lambda x: getattr(x, 'distance_km', float('inf')))
        
        # Serialize results
        serializer = ScrapedRestaurantListSerializer(restaurants, many=True)
        
        # Add distance to serialized data if available
        data = serializer.data
        if latitude and longitude:
            for i, restaurant in enumerate(restaurants):
                if hasattr(restaurant, 'distance_km'):
                    data[i]['distance_km'] = restaurant.distance_km
        
        return Response({
            'count': len(data),
            'results': data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error fetching scraped restaurants: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to fetch restaurants: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])
def get_scraped_restaurant_detail(request, restaurant_id):
    """Get detailed information about a specific scraped restaurant"""
    try:
        restaurant = ScrapedRestaurant.objects.get(id=restaurant_id, is_active=True)
        serializer = ScrapedRestaurantSerializer(restaurant)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except ScrapedRestaurant.DoesNotExist:
        return Response(
            {"error": "Restaurant not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to fetch restaurant: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([])
def create_scraped_restaurant(request):
    """Create a new scraped restaurant entry"""
    try:
        serializer = ScrapedRestaurantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response(
            {"error": f"Failed to create restaurant: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ============================================================================
# Discovery & Pre-Created Itineraries
# ============================================================================

@api_view(['GET'])
@permission_classes([])
def get_pre_created_itineraries(request):
    """
    Get pre-created itineraries with optional filtering.
    
    Query params:
    - cuisine: Filter by cuisine type
    - price_range: Filter by price range
    - min_rating: Minimum rating
    - tags: Comma-separated tags
    - latitude: User latitude (for location filtering)
    - longitude: User longitude (for location filtering)
    - radius_km: Search radius in km
    """
    try:
        # Get filter parameters
        cuisine = request.GET.get('cuisine', '').strip()
        price_range = request.GET.get('price_range', '').strip()
        min_rating = float(request.GET.get('min_rating', 0))
        tags_str = request.GET.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        radius_km = float(request.GET.get('radius_km', 10.0))  # Default 10km
        
        # Start with all pre-created itineraries
        queryset = PreCreatedItinerary.objects.all()
        
        # Apply filters
        if cuisine:
            queryset = queryset.filter(cuisine__icontains=cuisine)
        
        if price_range:
            queryset = queryset.filter(price_range=price_range)
        
        if min_rating > 0:
            queryset = queryset.filter(min_rating__gte=min_rating)
        
        if tags:
            # Filter by tags (check if any tag matches)
            from django.db.models import Q
            tag_filter = Q()
            for tag in tags:
                tag_filter |= Q(tags__icontains=tag)
            queryset = queryset.filter(tag_filter)
        
        # Location-based filtering (if provided)
        if latitude and longitude:
            try:
                user_lat = float(latitude)
                user_lng = float(longitude)
                
                # Filter by radius (simple bounding box approximation)
                # 1 degree latitude ≈ 111 km
                lat_range = radius_km / 111.0
                lng_range = radius_km / (111.0 * abs(math.cos(math.radians(user_lat))))
                
                queryset = queryset.filter(
                    latitude__range=(user_lat - lat_range, user_lat + lat_range),
                    longitude__range=(user_lng - lng_range, user_lng + lng_range)
                )
            except (ValueError, TypeError):
                pass  # Invalid coordinates, skip location filter
        
        # Limit results
        limit = int(request.GET.get('limit', 20))
        queryset = queryset[:limit]
        
        # Serialize results
        results = []
        for itinerary in queryset:
            results.append({
                'id': itinerary.id,
                'title': itinerary.title,
                'description': itinerary.description,
                'subtitle': f"{itinerary.neighborhood} • {itinerary.cuisine}" if itinerary.neighborhood and itinerary.cuisine else itinerary.neighborhood or itinerary.cuisine or '',
                'cuisine': itinerary.cuisine or '',
                'price_range': itinerary.price_range or '',
                'min_rating': float(itinerary.min_rating),
                'tags': itinerary.tags or [],
                'latitude': float(itinerary.latitude),
                'longitude': float(itinerary.longitude),
                'radius_km': float(itinerary.radius_km),
                'neighborhood': itinerary.neighborhood or '',
                'restaurant_count': itinerary.total_restaurants,
                'enriched_count': itinerary.enriched_count,
                'enrichment_percentage': float(itinerary.enrichment_percentage),
                'is_featured': itinerary.is_featured,
                'sample_image_url': itinerary.sample_image_url or '',
                'itinerary_data': itinerary.itinerary_data,  # Full itinerary data with restaurants
                'created_at': itinerary.created_at.isoformat(),
                'last_updated': itinerary.last_updated.isoformat(),
            })
        
        return Response({
            'itineraries': results,
            'total': len(results)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error getting pre-created itineraries: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to get pre-created itineraries: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([])
def pre_create_itineraries(request):
    """
    Pre-create itineraries for popular combinations.
    This is a background job that can be called manually or via cron.
    
    Creates itineraries for:
    - Italian + $30 and under + Neighborhood gem (East Village, 1km)
    - French + $31-$50 + Charming (TriBeCa, 3km)
    - Mexican + $30 and under + Good for groups (West Village, 1km)
    - Japanese + $50+ + Good for special occasions (Lower East Side, 3km)
    - Contemporary American + $31-$50 + Great for brunch (SoHo, 1km)
    """
    try:
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
                    # Note: We don't regenerate the itinerary here - that would require calling
                    # generate_and_enrich_itinerary which needs places from Google Places API
                    existing.save()
                    created_count += 1
                    continue
                
                # Create new (without itinerary data - will be populated when frontend calls generate)
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
                
            except Exception as e:
                errors.append(f"Error creating {combo['title']}: {str(e)}")
        
        return Response({
            'created': created_count,
            'errors': errors,
            'message': f'Successfully created/updated {created_count} pre-created itineraries'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error pre-creating itineraries: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to pre-create itineraries: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([])
def get_featured_itineraries(request):
    """
    Get featured pre-created itineraries for home page.
    Returns 6-8 featured itineraries with full itinerary data.
    
    Query params:
    - limit: Number of itineraries to return (default: 8)
    - include_all: If true, also return non-featured itineraries (default: false)
    """
    try:
        limit = int(request.GET.get('limit', 8))
        include_all = request.GET.get('include_all', 'false').lower() == 'true'
        
        # Get featured itineraries
        featured = PreCreatedItinerary.objects.filter(
            is_featured=True
        ).order_by('-created_at')[:limit]
        
        results = []
        for itinerary in featured:
            results.append({
                'id': itinerary.id,
                'title': itinerary.title,
                'description': itinerary.description,
                'subtitle': f"{itinerary.neighborhood} • {itinerary.cuisine}" if itinerary.neighborhood and itinerary.cuisine else itinerary.neighborhood or itinerary.cuisine or '',
                'cuisine': itinerary.cuisine or '',
                'price_range': itinerary.price_range or '',
                'neighborhood': itinerary.neighborhood or '',
                'restaurant_count': itinerary.total_restaurants,
                'enriched_count': itinerary.enriched_count,
                'enrichment_percentage': float(itinerary.enrichment_percentage),
                'sample_image_url': itinerary.sample_image_url or '',
                'latitude': float(itinerary.latitude),
                'longitude': float(itinerary.longitude),
                'radius_km': float(itinerary.radius_km),
                'tags': itinerary.tags or [],
                'is_featured': itinerary.is_featured,
                'itinerary_data': itinerary.itinerary_data,  # Full itinerary data with restaurants
                'created_at': itinerary.created_at.isoformat(),
            })
        
        # If include_all is true, also get non-featured itineraries
        all_itineraries = []
        if include_all:
            non_featured = PreCreatedItinerary.objects.filter(
                is_featured=False
            ).order_by('-created_at')[:limit]
            
            for itinerary in non_featured:
                all_itineraries.append({
                    'id': itinerary.id,
                    'title': itinerary.title,
                    'description': itinerary.description,
                    'subtitle': f"{itinerary.neighborhood} • {itinerary.cuisine}" if itinerary.neighborhood and itinerary.cuisine else itinerary.neighborhood or itinerary.cuisine or '',
                    'cuisine': itinerary.cuisine or '',
                    'price_range': itinerary.price_range or '',
                    'neighborhood': itinerary.neighborhood or '',
                    'restaurant_count': itinerary.total_restaurants,
                    'enriched_count': itinerary.enriched_count,
                    'enrichment_percentage': float(itinerary.enrichment_percentage),
                    'sample_image_url': itinerary.sample_image_url or '',
                    'latitude': float(itinerary.latitude),
                    'longitude': float(itinerary.longitude),
                    'radius_km': float(itinerary.radius_km),
                    'tags': itinerary.tags or [],
                    'is_featured': itinerary.is_featured,
                    'itinerary_data': itinerary.itinerary_data,
                    'created_at': itinerary.created_at.isoformat(),
                })
        
        return Response({
            'featured_itineraries': results,
            'all_itineraries': all_itineraries if include_all else [],
            'total_featured': len(results),
            'total_all': len(results) + len(all_itineraries) if include_all else len(results)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error getting featured itineraries: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to get featured itineraries: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])
def get_pre_created_itinerary_detail(request, itinerary_id):
    """
    Get detailed information about a specific pre-created itinerary.
    Returns full itinerary data including all restaurants.
    """
    try:
        itinerary = PreCreatedItinerary.objects.get(id=itinerary_id)
        
        return Response({
            'id': itinerary.id,
            'title': itinerary.title,
            'description': itinerary.description,
            'subtitle': f"{itinerary.neighborhood} • {itinerary.cuisine}" if itinerary.neighborhood and itinerary.cuisine else itinerary.neighborhood or itinerary.cuisine or '',
            'cuisine': itinerary.cuisine or '',
            'price_range': itinerary.price_range or '',
            'min_rating': float(itinerary.min_rating),
            'neighborhood': itinerary.neighborhood or '',
            'restaurant_count': itinerary.total_restaurants,
            'enriched_count': itinerary.enriched_count,
            'enrichment_percentage': float(itinerary.enrichment_percentage),
            'sample_image_url': itinerary.sample_image_url or '',
            'latitude': float(itinerary.latitude),
            'longitude': float(itinerary.longitude),
            'radius_km': float(itinerary.radius_km),
            'tags': itinerary.tags or [],
            'is_featured': itinerary.is_featured,
            'itinerary_data': itinerary.itinerary_data,  # Full itinerary with restaurants
            'created_at': itinerary.created_at.isoformat(),
            'last_updated': itinerary.last_updated.isoformat(),
        }, status=status.HTTP_200_OK)
        
    except PreCreatedItinerary.DoesNotExist:
        return Response(
            {"error": "Itinerary not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import traceback
        print(f"DEBUG: Error getting itinerary detail: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to get itinerary detail: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )