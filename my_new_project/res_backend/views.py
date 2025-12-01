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
from .models import Establishment, EstablishmentFeature
from .serializers import EstablishmentSerializer, EstablishmentFeatureSerializer
from django.shortcuts import get_object_or_404
from .recommendation import RestaurantRecommender
import uuid

# Initialize Firebase app (if not already initialized)
# Supports both environment variable (Railway) and file path (local dev)
if not firebase_admin._apps:
    import os
    import json
    
    # Try to get credentials from environment variable first (for Railway)
    firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS')
    
    if firebase_creds_json:
        # Parse JSON string from environment variable
        try:
            # Handle both string and already-parsed JSON
            if isinstance(firebase_creds_json, str):
                cred_dict = json.loads(firebase_creds_json)
            else:
                cred_dict = firebase_creds_json
            
            cred = credentials.Certificate(cred_dict)
            print("DEBUG: Initialized Firebase using environment variable")
            print(f"DEBUG: Firebase project_id: {cred_dict.get('project_id', 'unknown')}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"ERROR: Failed to parse FIREBASE_CREDENTIALS: {str(e)}")
            print(f"ERROR: FIREBASE_CREDENTIALS length: {len(firebase_creds_json) if firebase_creds_json else 0}")
            print(f"ERROR: First 100 chars: {firebase_creds_json[:100] if firebase_creds_json else 'None'}")
            raise
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
                raise FileNotFoundError(
                    f"Firebase credentials not found. Set FIREBASE_CREDENTIALS environment variable or place credentials file at {SERVICE_ACCOUNT_PATH}"
                )
    
    firebase_admin.initialize_app(cred)

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
        
        print(f"DEBUG: Attempting to add document to Firestore...")
        import time
        start_time = time.time()
        
        try:
            # Firestore add() returns (write_result, document_reference)
            write_result, doc_ref = db.collection('public_itineraries').add(itinerary_data)
            itinerary_id = doc_ref.id
            elapsed = time.time() - start_time
            print(f"DEBUG: Successfully created document with ID: {itinerary_id} in {elapsed:.2f}s")
        except Exception as firestore_error:
            print(f"DEBUG: Firestore error: {str(firestore_error)}")
            import traceback
            print(f"DEBUG: Firestore traceback: {traceback.format_exc()}")
            raise firestore_error
        
        # Update user stats (non-blocking - don't wait for this to complete)
        # Return response immediately, update stats in background
        try:
            user_stats_ref = db.collection('user_stats').document(user_id)
            user_stats_doc = user_stats_ref.get()
            
            if user_stats_doc.exists:
                # Use update which is faster than get + update
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
            print(f"DEBUG: User stats updated successfully")
        except Exception as stats_error:
            # Don't fail the request if stats update fails
            print(f"WARNING: Failed to update user stats (non-critical): {str(stats_error)}")
        
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
        location = request.query_params.get('location', '').strip()
        categories_str = request.query_params.get('categories', '')
        categories = [c.strip() for c in categories_str.split(',') if c.strip()] if categories_str else []
        sort_by = request.query_params.get('sort', 'recent')  # 'likes' or 'recent'
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        # Build query
        query = db.collection('public_itineraries').where('status', '==', 'approved')
        
        # Filter by location (case-insensitive partial match)
        if location:
            # Firestore doesn't support case-insensitive search directly
            # We'll filter in Python after fetching
            pass
        
        # Filter by categories (if any category matches)
        if categories:
            # Firestore 'in' query can only check one category at a time
            # We'll filter in Python after fetching
            pass
        
        # Execute query
        docs = query.stream()
        
        # Convert to list and filter
        itineraries = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            
            # Filter by location
            if location:
                if location.lower() not in data.get('location', '').lower():
                    continue
            
            # Filter by categories (if any category matches)
            if categories:
                itinerary_categories = [c.lower() for c in data.get('categories', [])]
                if not any(cat.lower() in itinerary_categories for cat in categories):
                    continue
            
            # Get user stats
            user_id = data.get('user_id')
            user_stats_doc = db.collection('user_stats').document(user_id).get()
            if user_stats_doc.exists:
                stats = user_stats_doc.to_dict()
                data['user_stats'] = {
                    'total_public_itineraries': stats.get('total_public_itineraries', 0),
                    'total_likes_received': stats.get('total_likes_received', 0),
                }
            else:
                data['user_stats'] = {
                    'total_public_itineraries': 0,
                    'total_likes_received': 0,
                }
            
            itineraries.append(data)
        
        # Sort
        if sort_by == 'likes':
            itineraries.sort(key=lambda x: x.get('likes_count', 0), reverse=True)
        else:  # recent
            itineraries.sort(key=lambda x: x.get('created_at'), reverse=True)
        
        # Paginate
        total = len(itineraries)
        itineraries = itineraries[offset:offset + limit]
        
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
            'saved_itinerary_id': saved_ref[1].id,
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