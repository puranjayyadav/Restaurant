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
import math
from typing import List, Dict
from django.shortcuts import get_object_or_404
import requests
from .recommendation import RestaurantRecommender
from .utils import (
    match_restaurant_with_postgres, enrich_restaurant_data,
    filter_directional_places, get_time_context_query, get_time_context_label
)
from .scraping_service import get_cached_or_scraped_places
from .geohash_cache import (
    get_geohash, get_cached_places, save_places_to_cache,
    get_neighborhood_cluster_rpc, get_curated_places_from_lemon8
)
from .nba_solver import NBASolver, DynamicItinerarySolver
from .itinerary_engine import ItineraryEngine
import uuid
import json
from datetime import datetime

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
                print(f"WARNING: {error_msg}")
                cred = None
                
    if cred:
        try:
            firebase_admin.initialize_app(cred)
            print("DEBUG: Firebase app initialized successfully")
        except Exception as init_error:
            print(f"ERROR: Failed to initialize Firebase app: {str(init_error)}")
            cred = None

# Get a Firestore client
db = firestore.client() if cred else None

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

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def get_hotspot_itinerary(request):
    """
    Just-in-Time Itinerary Generation for a specific map hotspot.
    Triggered when a user taps a cluster on the density heatmap.
    """
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        vibe = request.GET.get('vibe', 'Trendy')
        radius_km = float(request.GET.get('radius_km', 1.5))
    except (TypeError, ValueError):
        return Response({"error": "Invalid lat/lng/radius"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. Fetch curated candidates from Supabase (Lemon8 Table)
        from supabase import create_client
        import os
        from decouple import config
        from .models import ScrapedRestaurant
        
        url = config("SUPABASE_URL", default=os.getenv("SUPABASE_URL"))
        key = config("SUPABASE_KEY", default=os.getenv("SUPABASE_KEY"))
        candidates_data = []

        if url and key:
            try:
                supabase = create_client(url, key)
                # Query curated articles
                response = (
                    supabase.table("lemon8_articles")
                    .select("url, enriched_itinerary_data")
                    .not_.is_("enriched_itinerary_data", "null")
                    .execute()
                )
                candidates_data = response.data or []
                print(f"[Hotspot] Lemon8 candidates: {len(candidates_data)}")
            except Exception as se:
                print(f"[Hotspot] Supabase fetch failed: {se}")
        else:
            print("[Hotspot] Skipping Supabase: Credentials missing.")
        
        # 2. Add high-quality local restaurants from PostgreSQL (EXPANDED POOL)
        # Search radius: ~5km (0.05 degrees) for much more variety
        local_spots = ScrapedRestaurant.objects.filter(
            latitude__range=(lat-0.05, lat+0.05),
            longitude__range=(lng-0.05, lng+0.05),
            rating__gte=3.5  # Lowered from 4.0 to include more variety
        )[:100]  # Increased from 20 to 100
        
        print(f"[Hotspot] PostgreSQL candidates: {local_spots.count()}")
        
        for spot in local_spots:
            # Wrap in a format the ItineraryEngine expects
            candidates_data.append({
                'enriched_itinerary_data': {
                    'stops': [{
                        'place_name': spot.name,
                        'latitude': float(spot.latitude),
                        'longitude': float(spot.longitude),
                        'notes': spot.description or f"Top rated spot in {spot.city}",
                        'rating': float(spot.rating),
                        'vibe_tags': spot.categories if isinstance(spot.categories, list) else [],
                        'solver_data': {
                            'price_tier': spot.price_range or '$$',
                            'time_bias': 'Anytime',
                            'category_normalized': spot.categories[0] if spot.categories else 'Restaurant'
                        }
                    }]
                }
            })

        # 3. Drop all into the Engine
        engine = ItineraryEngine(candidates_data)
        
        # 4. Generate the Plan
        plan = engine.generate_plan(lat, lng, selected_vibe=vibe)
        
        if "error" in plan:
            return Response(plan, status=status.HTTP_404_NOT_FOUND)
            
        return Response(plan, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"ERROR in get_hotspot_itinerary: {e}")
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
    Uses OR-Tools optimization if enabled, with seamless fallback to rule-based algorithm.
    """
    import math
    import json
    import os
    from django.conf import settings
    from res_backend.routing_service import RoutingService
    from res_backend.or_tools_solver import TOPTWSolver
    from res_backend.utils import (
        calculate_restaurant_score, 
        calculate_visit_duration, 
        get_time_windows_for_categories
    )
    from res_backend.clustering_service import find_walkable_neighborhoods
    
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        
        user_id = data.get('user_id')
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        selected_categories = data.get('selected_categories', [])
        max_distance_km = float(data.get('max_distance_km', 1.0))  # Default 1 km between places
        places_data = data.get('places', [])  # Places fetched from Google API by Flutter
        vegetarian_filter = data.get('vegetarian_filter', False)  # Vegetarian filter option
        
        # Feature flag: Use OR-Tools optimizer if enabled
        USE_OR_TOOLS_OPTIMIZER = os.getenv('USE_OR_TOOLS_OPTIMIZER', 'false').lower() == 'true'
        USE_OR_TOOLS_OPTIMIZER = getattr(settings, 'USE_OR_TOOLS_OPTIMIZER', USE_OR_TOOLS_OPTIMIZER)

        # Clustering feature flags
        ENABLE_CLUSTERING = getattr(settings, 'ENABLE_CLUSTERING', True)
        ENABLE_GAP_FILLING = getattr(settings, 'ENABLE_GAP_FILLING', True)
        MAX_CLUSTERS_TO_USE = int(getattr(settings, 'MAX_CLUSTERS_TO_USE', 3))
        CLUSTER_STRATEGY = getattr(settings, 'CLUSTER_STRATEGY', 'single')
        
        print(f"DEBUG: Using max distance: {max_distance_km}km between places")
        print(f"DEBUG: OR-Tools optimizer enabled: {USE_OR_TOOLS_OPTIMIZER}")
        print(f"DEBUG: Clustering enabled: {ENABLE_CLUSTERING}, gap filling: {ENABLE_GAP_FILLING}, max clusters: {MAX_CLUSTERS_TO_USE}, strategy: {CLUSTER_STRATEGY}")
        
        if not places_data:
            return Response(
                {"error": "No places provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # HYBRID FETCH STRATEGY: Merge scraper results with database places
        print(f"DEBUG: Starting hybrid fetch - {len(places_data)} scraper results")
        
        # Fetch nearby saved places from Supabase (Stream B)
        radius_meters = int(max_distance_km * 1000 * 2)  # 2x radius for DB fetch (wider net)
        saved_places = _fetch_nearby_saved_places(latitude, longitude, radius_meters)
        print(f"DEBUG: Fetched {len(saved_places)} saved places from database")
        
        # Merge scraper results (Stream A) with database places (Stream B)
        merged_places = _merge_scraper_and_database_places(
            places_data, saved_places, latitude, longitude
        )
        print(f"DEBUG: After hybrid merge: {len(merged_places)} total unique places")
        
        # Convert merged places to Google Places format for compatibility
        # The merge function already handles format conversion, but ensure geometry structure
        for place in merged_places:
            # Ensure geometry structure exists for distance calculations
            if 'geometry' not in place or 'location' not in place.get('geometry', {}):
                lat = place.get('lat') or place.get('latitude')
                lng = place.get('long') or place.get('lng') or place.get('longitude')
                if lat and lng:
                    place['geometry'] = {
                        'location': {
                            'lat': float(lat),
                            'lng': float(lng)
                        }
                    }
        
        # Try OR-Tools path first (if enabled)
        if USE_OR_TOOLS_OPTIMIZER:
            try:
                places_for_solver = merged_places
                cluster_metadata = None

                if ENABLE_CLUSTERING:
                    clusters = find_walkable_neighborhoods(
                        merged_places,
                        user_location=(latitude, longitude),
                        enable_gap_filling=ENABLE_GAP_FILLING,
                        top_k=MAX_CLUSTERS_TO_USE,
                    )
                    if clusters:
                        if CLUSTER_STRATEGY == 'single':
                            # Deep dive in the single best neighborhood
                            best_cluster = clusters[0]
                            places_for_solver = best_cluster.get('places', []) or merged_places
                            cluster_metadata = {
                                'strategy': 'single',
                                'best_cluster_label': best_cluster.get('label'),
                                'best_cluster_score': best_cluster.get('composite_score'),
                                'best_cluster_size': best_cluster.get('size'),
                                'best_cluster_meta_verticals': best_cluster.get('meta_verticals', []),
                                'gap_filled': bool(best_cluster.get('gap_filled')),
                            }
                        else:
                            # Optional multi-neighborhood mode – flatten top_k clusters,
                            # but keep track of cluster ids for potential penalties.
                            selected = clusters[: max(1, MAX_CLUSTERS_TO_USE)]
                            flat_places: List[Dict] = []
                            for cl in selected:
                                for p in cl.get('places', []):
                                    p_with_cluster = dict(p)
                                    p_with_cluster['cluster_id'] = cl.get('label')
                                    flat_places.append(p_with_cluster)
                            if flat_places:
                                places_for_solver = flat_places
                                cluster_metadata = {
                                    'strategy': 'multi_penalized',
                                    'cluster_labels': [c.get('label') for c in selected],
                                }

                result = _generate_with_or_tools(
                    places_for_solver,
                    latitude,
                    longitude,
                    selected_categories,
                    max_distance_km,
                    vegetarian_filter,
                    user_id,
                    use_seen_history=True,
                    cluster_strategy=CLUSTER_STRATEGY,
                )
                if result:
                    meta = {'algorithm': 'or_tools', 'clustering': 'dbscan' if ENABLE_CLUSTERING else 'none'}
                    if cluster_metadata:
                        meta['cluster_metadata'] = cluster_metadata
                    result['metadata'] = meta
                    return Response(result, status=status.HTTP_200_OK)
                else:
                    print("DEBUG: OR-Tools returned no solution, falling back to rule-based")
            except Exception as e:
                import traceback
                print(f"DEBUG: OR-Tools failed: {str(e)}")
                print(f"DEBUG: {traceback.format_exc()}")
                print("DEBUG: Falling back to rule-based algorithm")
        
        # Fallback to rule-based algorithm (existing logic)
        return _generate_rule_based_itinerary(
            merged_places, latitude, longitude, selected_categories,
            max_distance_km, vegetarian_filter
        )
        
    except Exception as e:
        import traceback
        print(f"DEBUG: Error generating itinerary: {str(e)}")
        print(f"DEBUG: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to generate itinerary: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _normalize_phone(phone_str, country_code='US'):
    """
    Normalize phone number to E.164 format for reliable matching.
    Uses phonenumbers library (Google's libphonenumber port) if available.
    Falls back to simple normalization if library not installed.
    """
    if not phone_str:
        return None
    
    try:
        import phonenumbers
        # Parse the number, assuming US as default region
        parsed_num = phonenumbers.parse(str(phone_str), country_code)
        
        # Format to E.164 standard (e.g., +12125551212)
        if phonenumbers.is_valid_number(parsed_num):
            return phonenumbers.format_number(parsed_num, phonenumbers.PhoneNumberFormat.E164)
    except ImportError:
        # Fallback: simple normalization if library not available
        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in str(phone_str) if c.isdigit() or c == '+')
        if cleaned:
            if not cleaned.startswith('+'):
                # Assume US if no country code
                if len(cleaned) == 10:
                    cleaned = '+1' + cleaned
                elif len(cleaned) == 11 and cleaned.startswith('1'):
                    cleaned = '+' + cleaned
            return cleaned
    except Exception as e:
        print(f"DEBUG: Error normalizing phone {phone_str}: {e}")
    
    return None


def _fetch_nearby_saved_places(lat, lng, radius_meters=2000):
    """
    Fetch nearby saved places from Supabase using spatial query.
    This is Layer 1 of the Hybrid Fetch strategy - efficiently get only relevant DB rows.
    
    Returns:
        List of place dictionaries from Supabase
    """
    try:
        # Import supabase config
        import sys
        import os
        # Add parent directory to path to import supabase_config
        parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from supabase_config import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            print("DEBUG: Supabase client not available, skipping database fetch")
            return []
        
        # Try to use RPC function if it exists, otherwise fallback to client-side filtering
        # Try combined RPC function first (fetches from all sources)
        try:
            result = supabase.rpc('get_nearby_saved_places_all', {
                'lat': float(lat),
                'lng': float(lng),
                'radius_meters': int(radius_meters)
            }).execute()
            
            if result.data:
                print(f"DEBUG: Fetched {len(result.data)} nearby places from Supabase (combined RPC)")
                return result.data
        except Exception as combined_rpc_error:
            print(f"DEBUG: Combined RPC not available, trying individual RPCs: {combined_rpc_error}")
        
        # Try individual RPC functions
        all_places = []
        yelp_rpc_error = None
        scraped_rpc_error = None
        
        # Try yelp_restaurants RPC
        try:
            result = supabase.rpc('get_nearby_saved_places_yelp', {
                'lat': float(lat),
                'lng': float(lng),
                'radius_meters': int(radius_meters)
            }).execute()
            
            if result.data:
                print(f"DEBUG: Fetched {len(result.data)} places from yelp_restaurants (RPC)")
                all_places.extend(result.data)
        except Exception as e:
            yelp_rpc_error = e
            print(f"DEBUG: Yelp RPC not available: {e}")
        
        # Try scraped restaurants RPC (OpenTable, etc.)
        try:
            result = supabase.rpc('get_nearby_saved_places_scraped', {
                'lat': float(lat),
                'lng': float(lng),
                'radius_meters': int(radius_meters)
            }).execute()
            
            if result.data:
                print(f"DEBUG: Fetched {len(result.data)} places from res_backend_scrapedrestaurant (RPC)")
                all_places.extend(result.data)
        except Exception as e:
            scraped_rpc_error = e
            print(f"DEBUG: Scraped RPC not available: {e}")
        
        if all_places:
            print(f"DEBUG: Total fetched from RPCs: {len(all_places)} places")
            return all_places
        
        # Fallback to client-side filtering
        print(f"DEBUG: RPC functions not available, using client-side filtering")
        all_places = []
        
        # Try yelp_restaurants table
        try:
            yelp_result = supabase.table('yelp_restaurants').select('*').limit(1000).execute()
            
            if yelp_result.data:
                # Filter by distance client-side
                from res_backend.utils import haversine_distance
                nearby = []
                for place in yelp_result.data:
                            # Handle location as JSONB or dict
                            location = place.get('location')
                            if isinstance(location, dict):
                                place_lat = location.get('lat')
                                place_lng = location.get('lng')
                            elif isinstance(location, str):
                                import json
                                try:
                                    location_dict = json.loads(location)
                                    place_lat = location_dict.get('lat')
                                    place_lng = location_dict.get('lng')
                                except:
                                    place_lat = None
                                    place_lng = None
                            else:
                                place_lat = None
                                place_lng = None
                            
                            # Also check for direct lat/lng fields (if table has them)
                            if not place_lat:
                                place_lat = place.get('latitude') or place.get('lat')
                            if not place_lng:
                                place_lng = place.get('longitude') or place.get('lng') or place.get('long')
                            
                            if place_lat and place_lng:
                                try:
                                    distance_m = haversine_distance(lat, lng, float(place_lat), float(place_lng))
                                    if distance_m <= radius_meters:
                                        # Convert to Google Places format for compatibility
                                        place['google_place_id'] = place.get('yelp_id')  # Use yelp_id as identifier
                                        place['place_id'] = place.get('yelp_id')
                                        # Ensure geometry structure
                                        place['geometry'] = {
                                            'location': {
                                                'lat': float(place_lat),
                                                'lng': float(place_lng)
                                            }
                                        }
                                        # Map fields to Google Places format
                                        place['name'] = place.get('name', '')
                                        place['formatted_address'] = place.get('address', '')
                                        place['rating'] = place.get('rating')
                                        place['user_ratings_total'] = place.get('total_reviews') or place.get('review_count')
                                        place['types'] = place.get('categories', [])
                                        place['photos'] = place.get('photos', []) or place.get('image_urls', [])
                                        nearby.append(place)
                                except (ValueError, TypeError) as e:
                                    print(f"DEBUG: Error processing place {place.get('name')}: {e}")
                                    continue
                        
                print(f"DEBUG: Fetched {len(nearby)} nearby places from yelp_restaurants (client-side filter)")
                all_places.extend(nearby)
        except Exception as e:
            print(f"DEBUG: Error fetching yelp_restaurants: {e}")
        
        # Also fetch from res_backend_scrapedrestaurant (OpenTable, etc.)
        try:
            scraped_places = supabase.table('res_backend_scrapedrestaurant').select('*').eq('is_active', True).is_('duplicate_of_id', 'null').limit(1000).execute()
            
            if scraped_places.data:
                from res_backend.utils import haversine_distance
                nearby_scraped = []
                for place in scraped_places.data:
                    place_lat = place.get('latitude')
                    place_lng = place.get('longitude')
                    
                    if place_lat and place_lng:
                        try:
                            distance_m = haversine_distance(lat, lng, float(place_lat), float(place_lng))
                            if distance_m <= radius_meters:
                                # Convert to Google Places format for compatibility
                                place['google_place_id'] = place.get('source_id') or f"scraped_{place.get('id')}"
                                place['place_id'] = place.get('google_place_id')
                                # Extract google_place_id from raw_data if available
                                if place.get('raw_data') and isinstance(place.get('raw_data'), dict):
                                    raw_place_id = place['raw_data'].get('place_id') or place['raw_data'].get('google_place_id')
                                    if raw_place_id:
                                        place['google_place_id'] = raw_place_id
                                        place['place_id'] = raw_place_id
                                
                                # Ensure geometry structure
                                place['geometry'] = {
                                    'location': {
                                        'lat': float(place_lat),
                                        'lng': float(place_lng)
                                    }
                                }
                                # Map fields to Google Places format
                                place['name'] = place.get('name', '')
                                place['formatted_address'] = place.get('address', '')
                                place['rating'] = float(place.get('rating')) if place.get('rating') else None
                                place['user_ratings_total'] = place.get('total_reviews', 0)
                                place['types'] = place.get('categories', [])
                                place['photos'] = place.get('photos', [])
                                place['source_type'] = place.get('source', 'other')  # Track source (opentable, etc.)
                                nearby_scraped.append(place)
                        except (ValueError, TypeError) as e:
                            print(f"DEBUG: Error processing scraped place {place.get('name')}: {e}")
                            continue
                
                print(f"DEBUG: Fetched {len(nearby_scraped)} nearby places from res_backend_scrapedrestaurant (client-side filter)")
                all_places.extend(nearby_scraped)
        except Exception as e:
            print(f"DEBUG: Error fetching res_backend_scrapedrestaurant: {e}")
        
        if all_places:
            print(f"DEBUG: Total fetched from client-side filtering: {len(all_places)} places")
            return all_places
        
        return []
    except Exception as e:
        print(f"DEBUG: Error in _fetch_nearby_saved_places: {e}")
        import traceback
        print(f"DEBUG: {traceback.format_exc()}")
        return []


def _merge_scraper_and_database_places(scraper_results, saved_places, lat, lng):
    """
    Hybrid Fetch Strategy: Merge scraper results with database places.
    
    Strategy:
    1. Use google_place_id as primary key for deduplication
    2. Use normalized phone number as secondary key
    3. Database version wins when duplicate found (has curated data)
    4. Add bonus_score for database places
    
    Args:
        scraper_results: List of places from Google Maps scraper (Stream A)
        saved_places: List of places from Supabase database (Stream B)
        lat, lng: Center coordinates for distance calculations
    
    Returns:
        Merged list of places with deduplication applied
    """
    # Step 1: Normalize phone numbers in scraper results
    for place in scraper_results:
        raw_phone = place.get('phone') or place.get('formatted_phone_number') or place.get('phone_number')
        if raw_phone:
            place['normalized_phone'] = _normalize_phone(str(raw_phone))
        else:
            place['normalized_phone'] = None
    
    # Step 2: Create indices from database places
    # Index by google_place_id (primary key)
    db_by_place_id = {}
    # Index by normalized phone (secondary key)
    phone_index = {}
    
    for place in saved_places:
        # Normalize phone for database places
        raw_phone = place.get('phone') or place.get('formatted_phone_number')
        if raw_phone:
            normalized_phone = _normalize_phone(str(raw_phone))
            if normalized_phone:
                phone_index[normalized_phone] = place
        
        # Index by google_place_id if available
        # Check multiple possible locations for google_place_id
        google_place_id = (
            place.get('google_place_id') or 
            place.get('place_id') or
            (place.get('raw_data', {}).get('place_id') if isinstance(place.get('raw_data'), dict) else None) or
            (place.get('raw_data', {}).get('google_place_id') if isinstance(place.get('raw_data'), dict) else None)
        )
        if google_place_id:
            db_by_place_id[str(google_place_id)] = place
    
    # Step 3: Merge using "Zipper Merge" strategy
    merged_candidates = {}
    
    # Process scraper results (Stream A)
    for scraper_place in scraper_results:
        google_place_id = scraper_place.get('place_id') or scraper_place.get('google_place_id')
        normalized_phone = scraper_place.get('normalized_phone')
        
        # CASE 1: Primary Key Match (Google Place ID exists)
        if google_place_id:
            place_id_str = str(google_place_id)
            
            if place_id_str in db_by_place_id:
                # Database version wins - merge with scraper data as fallback
                db_place = db_by_place_id[place_id_str]
                merged_candidates[place_id_str] = {
                    **scraper_place,  # Start with scraper data
                    **db_place,  # Overwrite with database data (wins)
                    'source': 'database',
                    'is_saved': True,
                    'bonus_score': 10,  # Bonus for database places
                }
                print(f"DEBUG: Merged {scraper_place.get('name', 'Unknown')} - DB version wins (place_id match)")
            else:
                # New scraper result, not in database
                merged_candidates[place_id_str] = {
                    **scraper_place,
                    'source': 'scraper',
                    'is_saved': False,
                    'bonus_score': 0,
                }
        
        # CASE 2: Secondary Key Match (Google ID missing, but Phone exists)
        elif normalized_phone and normalized_phone in phone_index:
            db_match = phone_index[normalized_phone]
            db_google_id = db_match.get('google_place_id') or db_match.get('place_id')
            
            if db_google_id:
                # Use DB's Google ID as the merge key
                place_id_str = str(db_google_id)
                merged_candidates[place_id_str] = {
                    **scraper_place,  # Scraper data
                    **db_match,  # Database data wins
                    'source': 'database_match_by_phone',
                    'is_saved': True,
                    'bonus_score': 10,
                }
                print(f"DEBUG: Merged {scraper_place.get('name', 'Unknown')} - DB version wins (phone match)")
            else:
                # DB place has no Google ID, create temporary ID
                temp_id = f"phone_{normalized_phone}"
                merged_candidates[temp_id] = {
                    **scraper_place,
                    **db_match,
                    'source': 'database_match_by_phone',
                    'is_saved': True,
                    'bonus_score': 10,
                }
        
        # CASE 3: No match - new scraper result
        else:
            # Create temporary ID for places without place_id
            temp_id = scraper_place.get('name', 'unknown') + '_' + str(hash(str(scraper_place.get('lat', 0)) + str(scraper_place.get('lng', 0))))
            merged_candidates[temp_id] = {
                **scraper_place,
                'source': 'scraper',
                'is_saved': False,
                'bonus_score': 0,
            }
    
    # Step 4: Add database places that weren't in scraper results
    for db_place in saved_places:
        google_place_id = db_place.get('google_place_id') or db_place.get('place_id')
        if google_place_id:
            place_id_str = str(google_place_id)
            if place_id_str not in merged_candidates:
                # Database place not found in scraper results - add it
                merged_candidates[place_id_str] = {
                    **db_place,
                    'source': 'database_only',
                    'is_saved': True,
                    'bonus_score': 10,
                }
    
    print(f"DEBUG: Hybrid merge complete - {len(merged_candidates)} unique places")
    print(f"DEBUG:   - From scraper: {sum(1 for p in merged_candidates.values() if p.get('source') == 'scraper')}")
    print(f"DEBUG:   - From database: {sum(1 for p in merged_candidates.values() if p.get('is_saved'))}")
    
    return list(merged_candidates.values())


def _get_user_seen_place_ids(user_id):
    """
    Layer 2 Helper: Get list of place_ids the user has seen/interacted with.
    Returns a set of place_ids for efficient lookup.
    
    Since user_id is a Firebase UID (string), we query Firestore directly
    where the Flutter app stores establishments with user's UID.
    """
    if not user_id:
        return set()
    
    try:
        # Query Firestore for establishments associated with this user
        # Flutter app stores establishments in collectionGroup('establishments') with 'uid' field
        seen_place_ids = set()
        
        # Query Firestore for user's establishments
        establishments_query = db.collection_group('establishments').where('uid', '==', user_id).limit(1000).stream()
        
        for doc in establishments_query:
            data = doc.to_dict()
            # Extract place_id from the establishment data
            place_id = data.get('place_id') or data.get('id')
            if place_id:
                seen_place_ids.add(str(place_id))
        
        print(f"DEBUG: User {user_id} has seen {len(seen_place_ids)} places from Firestore")
        return seen_place_ids
    except Exception as e:
        print(f"DEBUG: Error fetching user seen places from Firestore: {e}")
        import traceback
        print(f"DEBUG: {traceback.format_exc()}")
        return set()


def _generate_with_or_tools(places_data, latitude, longitude, selected_categories,
                           max_distance_km, vegetarian_filter, user_id,
                           use_seen_history=True, cluster_strategy='single'):
    """
    Generate itinerary using OR-Tools optimization with 3-Layer Logic Stack.
    
    Layer 1 (Iron Dome): Hard geofence - only places within max_distance_km
    Layer 2 (Soft Decay): Apply 0.7 multiplier to scores of seen places
    Layer 3 (Emergency Reset): Check average score, reset if < 60
    
    Returns:
        Dict with itinerary data, or None if solver fails
    """
    from res_backend.routing_service import RoutingService
    from res_backend.or_tools_solver import TOPTWSolver
    from res_backend.utils import (
        calculate_restaurant_score, 
        calculate_visit_duration, 
        get_time_windows_for_categories
    )
    import math
    
    # Filter places by selected categories
    category_to_types = {
        'restaurants': ['restaurant', 'food', 'meal_takeaway'],
        'cafes': ['cafe', 'bakery'],
        'museums': ['museum', 'art_gallery'],
        'parks': ['park'],
        'shopping': ['shopping_mall', 'store'],
        'bars': ['bar', 'night_club', 'lounge'],
        'dessert': ['bakery', 'cafe']
    }
    
    allowed_types_set = set()
    for category in selected_categories:
        if category.lower() in category_to_types:
            allowed_types_set.update(category_to_types[category.lower()])
    
    filtered_places = []
    for place in places_data:
        place_types = [t.lower() for t in place.get('types', [])]
        if any(t in allowed_types_set for t in place_types):
            filtered_places.append(place)
    
    if not filtered_places:
        return None
    
    # Apply vegetarian filter if enabled
    if vegetarian_filter:
        vegetarian_keywords = ['vegetarian', 'vegan', 'plant-based', 'veggie']
        vegetarian_filtered = []
        for place in filtered_places:
            place_name = place.get('name', '').lower()
            place_description = place.get('description', '').lower()
            place_tags = [tag.lower() for tag in place.get('tags', [])]
            place_types = [t.lower() for t in place.get('types', [])]
            all_text = ' '.join([place_name, place_description] + place_tags + place_types)
            if any(keyword in all_text for keyword in vegetarian_keywords):
                vegetarian_filtered.append(place)
        filtered_places = vegetarian_filtered
    
    if not filtered_places:
        return None
    
    # CRITICAL: Filter places by max_distance_km from start location
    # This ensures hyper-local itineraries
    from res_backend.utils import haversine_distance
    start_location = (latitude, longitude)
    local_places = []
    distances_filtered = []
    
    for place in filtered_places:
        geometry = place.get('geometry', {})
        location = geometry.get('location', {})
        place_lat = location.get('lat')
        place_lng = location.get('lng')
        
        if place_lat and place_lng:
            # Calculate distance from start location
            distance_m = haversine_distance(latitude, longitude, place_lat, place_lng)
            distance_km = distance_m / 1000.0
            
            # Only include places within max_distance_km radius
            if distance_km <= max_distance_km:
                local_places.append(place)
            else:
                distances_filtered.append((place.get('name', 'Unknown'), distance_km))
    
    print(f"DEBUG: After distance filter ({max_distance_km}km): {len(local_places)} places remaining")
    if distances_filtered:
        print(f"DEBUG: Filtered out {len(distances_filtered)} places beyond {max_distance_km}km")
        # Show a few examples of filtered places
        for name, dist in distances_filtered[:3]:
            print(f"DEBUG:   - {name}: {dist:.2f}km away")
    
    if not local_places:
        print(f"DEBUG: No places within {max_distance_km}km of start location")
        return None
    
    # LAYER 2: Get user's seen places for soft decay
    seen_place_ids = set()
    if use_seen_history and user_id:
        seen_place_ids = _get_user_seen_place_ids(user_id)
    
    # Pre-process places: calculate scores, durations, time windows
    places = []
    scores = []
    durations = []
    time_windows = []
    
    for place in local_places:
        # Calculate utility score
        score = calculate_restaurant_score(place, filters=None, user_preferences=None)
        
        # Add bonus score for database places (from Hybrid Fetch)
        bonus_score = place.get('bonus_score', 0)
        if bonus_score > 0:
            score += bonus_score
            print(f"DEBUG: Bonus score +{bonus_score} for {place.get('name', 'Unknown')} (from database)")
        
        # LAYER 2: Apply soft decay (0.7 multiplier) to seen places
        place_id = place.get('place_id') or place.get('google_place_id', '')
        if place_id and str(place_id) in seen_place_ids:
            original_score = score
            score = score * 0.7  # 30% penalty for seen places
            print(f"DEBUG: Soft decay applied to {place.get('name', 'Unknown')}: {original_score:.1f} -> {score:.1f}")
        
        scores.append(score)
        
        # Calculate visit duration (function accepts place object)
        place_types = place.get('types', [])
        duration = calculate_visit_duration(place=place)
        durations.append(duration)
        
        # Get time window based on place categories and optional solver_data.time_bias
        time_window = get_time_windows_for_categories(
            place_types,
            solver_data=place.get('solver_data')
        )
        time_windows.append(time_window)
        places.append(place)
    
    # Build travel time matrix (cost-protected)
    routing_service = RoutingService()
    start_location = (latitude, longitude)
    
    try:
        time_matrix, original_indices = routing_service.get_travel_time_matrix(
            places, start_location, mode='walking', max_candidates=25, max_distance_km=max_distance_km
        )
    except Exception as e:
        print(f"DEBUG: Routing service failed: {e}")
        return None

    # Optional: penalize cluster switching when multi-neighborhood strategy is enabled.
    if cluster_strategy != 'single':
        try:
            cluster_ids = [p.get('cluster_id') for p in places]
            # Index 0 in time_matrix is the start location; places start at index 1.
            num_nodes = len(time_matrix)
            cluster_switch_penalty_minutes = 30  # ~0.5h extra for crossing neighborhoods
            for i in range(1, num_nodes):
                for j in range(1, num_nodes):
                    if i == j:
                        continue
                    ci = cluster_ids[i - 1] if i - 1 < len(cluster_ids) else None
                    cj = cluster_ids[j - 1] if j - 1 < len(cluster_ids) else None
                    if ci is not None and cj is not None and ci != cj:
                        time_matrix[i][j] += cluster_switch_penalty_minutes
        except Exception as e:
            print(f"DEBUG: Failed to apply cluster-switch penalty: {e}")
    
    # Set up constraints
    category_constraints = {
        'restaurant': 2,
        'food': 2,
        'cafe': 2,
        'museum': 1,
        'park': 1,
        'bar': 1,
    }
    
    # Solve with OR-Tools
    solver = TOPTWSolver()
    result = solver.solve_itinerary(
        places=places,
        time_matrix=time_matrix,
        scores=scores,
        durations=durations,
        time_windows=time_windows,
        category_constraints=category_constraints,
        start_location=start_location,
        time_budget=540,  # 9 hours
        slack_minutes=30,
        require_lunch=False,
        max_places=10,  # Limit to 8-10 places
        max_distance_km=max_distance_km  # Enforce hyper-local constraint
    )
    
    if not result:
        return None
    
    # Format output to match existing API response
    itinerary = []
    itinerary_scores = []  # Track scores for Layer 3 check
    previous_idx = 0  # Start location is index 0 in time_matrix
    
    for i, route_item in enumerate(result['route']):
        place_idx = route_item['place_index']
        if place_idx < len(places):
            place = places[place_idx]
            
            # Get the score for this place (for Layer 3 check)
            if place_idx < len(scores):
                itinerary_scores.append(scores[place_idx])
            
            # Convert arrival time (minutes from 00:00) to time string
            arrival_min = route_item['arrival_time']
            hours = arrival_min // 60
            minutes = arrival_min % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            geometry = place.get('geometry', {})
            location = geometry.get('location', {})
            
            # Calculate distance from previous place using time matrix
            # Convert travel time (minutes) to distance (km) assuming 5 km/h walking speed
            travel_time_min = 0
            if i == 0:
                # First place: travel time from start location (index 0) to first place
                # In time_matrix: start is 0, first place is 1, second is 2, etc.
                curr_matrix_idx = place_idx + 1
                if curr_matrix_idx < len(time_matrix) and curr_matrix_idx < len(time_matrix[0]):
                    travel_time_min = time_matrix[0][curr_matrix_idx]
            else:
                # Get travel time from previous place to current place
                # Previous place index in matrix: previous_idx + 1 (after start)
                # Current place index in matrix: place_idx + 1 (after start)
                prev_matrix_idx = previous_idx + 1
                curr_matrix_idx = place_idx + 1
                if (prev_matrix_idx < len(time_matrix) and 
                    curr_matrix_idx < len(time_matrix) and
                    curr_matrix_idx < len(time_matrix[prev_matrix_idx])):
                    travel_time_min = time_matrix[prev_matrix_idx][curr_matrix_idx]
            
            # Convert travel time to distance (5 km/h = 0.0833 km/min)
            distance_km = (travel_time_min * 0.0833) if travel_time_min > 0 else 0.0
            
            # Validate and recalculate distance using Haversine for accuracy
            # This ensures we have accurate distances between consecutive places
            from res_backend.utils import haversine_distance
            if i == 0:
                # Distance from start to first place
                start_lat, start_lng = start_location
                place_lat = location.get('lat')
                place_lng = location.get('lng')
                if place_lat and place_lng:
                    distance_m = haversine_distance(start_lat, start_lng, place_lat, place_lng)
                    distance_km = distance_m / 1000.0
            else:
                # Distance from previous place to current place
                prev_place = places[previous_idx]
                prev_geometry = prev_place.get('geometry', {})
                prev_location = prev_geometry.get('location', {})
                prev_lat = prev_location.get('lat')
                prev_lng = prev_location.get('lng')
                place_lat = location.get('lat')
                place_lng = location.get('lng')
                if prev_lat and prev_lng and place_lat and place_lng:
                    distance_m = haversine_distance(prev_lat, prev_lng, place_lat, place_lng)
                    distance_km = distance_m / 1000.0
                    
                    # Warn if distance exceeds max (shouldn't happen with proper constraints)
                    if distance_km > max_distance_km:
                        print(f"DEBUG: WARNING - Distance between places exceeds max: {distance_km:.2f}km > {max_distance_km}km")
            
            walk_time_minutes = int(travel_time_min) if travel_time_min > 0 else 0
            
            # Map time to slot name for Flutter compatibility
            # Flutter expects: 'morning', 'mid_day', 'afternoon', 'evening', or 'custom'
            slot_name = 'custom'
            if 540 <= arrival_min < 660:  # 09:00-11:00
                slot_name = 'morning'
            elif 660 <= arrival_min < 840:  # 11:00-14:00
                slot_name = 'mid_day'
            elif 840 <= arrival_min < 1020:  # 14:00-17:00
                slot_name = 'afternoon'
            elif 1020 <= arrival_min < 1200:  # 17:00-20:00
                slot_name = 'evening'
            
            # Ensure all fields are properly typed and not None
            place_name = place.get('name') or 'Unknown'
            place_id = place.get('place_id') or place.get('id') or ''
            lat = location.get('lat')
            lng = location.get('lng')
            address = place.get('vicinity') or place.get('formatted_address') or 'Address not available'
            types_list = place.get('types') or []
            photos_list = place.get('photos') or []
            
            # Ensure types and photos are lists
            if not isinstance(types_list, list):
                types_list = []
            if not isinstance(photos_list, list):
                photos_list = []
            
            itinerary_item = {
                'slot_name': slot_name,
                'start_time': time_str,
                'place_name': str(place_name),
                'place_id': str(place_id) if place_id else '',
                'latitude': float(lat) if lat is not None else None,
                'longitude': float(lng) if lng is not None else None,
                'address': str(address),
                'distance_from_previous': round(distance_km, 2),
                'estimated_walk_time': walk_time_minutes,
                'types': types_list,
                'photos': photos_list,
            }
            itinerary.append(itinerary_item)
            previous_idx = place_idx
    
    # LAYER 3: Emergency Reset - Check average score
    if itinerary_scores:
        average_score = sum(itinerary_scores) / len(itinerary_scores)
        print(f"DEBUG: Layer 3 - Average itinerary score: {average_score:.1f}")
        
        if average_score < 60 and use_seen_history and user_id:
            print(f"DEBUG: Layer 3 - Emergency Reset triggered! Average score {average_score:.1f} < 60")
            print(f"DEBUG: Layer 3 - Re-running without seen history penalty")
            
            # Re-run without soft decay (use_seen_history=False)
            reset_result = _generate_with_or_tools(
                places_data, latitude, longitude, selected_categories,
                max_distance_km, vegetarian_filter, user_id, use_seen_history=False
            )
            
            if reset_result and reset_result.get('itinerary'):
                reset_scores = []
                for item in reset_result['itinerary']:
                    # Recalculate score for reset itinerary items
                    place_id = item.get('place_id', '')
                    # Find the place in local_places and recalculate score
                    for place in local_places:
                        if str(place.get('place_id', '')) == str(place_id):
                            reset_scores.append(calculate_restaurant_score(place, filters=None, user_preferences=None))
                            break
                
                if reset_scores:
                    reset_avg = sum(reset_scores) / len(reset_scores)
                    print(f"DEBUG: Layer 3 - Reset itinerary average score: {reset_avg:.1f}")
                    
                    # Only use reset if it's better
                    if reset_avg >= 60:
                        print(f"DEBUG: Layer 3 - Using reset itinerary (score improved)")
                        return reset_result
                    else:
                        print(f"DEBUG: Layer 3 - Reset still below 60, using original")
    
    return {
        'itinerary': itinerary,
        'total_items': len(itinerary),
        'neighborhood': 'Local Area',
        'total_score': result['total_score'],
        'total_time': result['total_time'],
    }


def _generate_rule_based_itinerary(places_data, latitude, longitude, selected_categories,
                                   max_distance_km, vegetarian_filter):
    """
    Original rule-based itinerary generation algorithm (ghost fallback).
    This is the proven, reliable algorithm that always works.
    """
    import math
    import random
    
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
    
    print(f"DEBUG: Total places received: {len(places_data)}")
    
    # Filter places by selected categories (using allowed_types_set built above)
    filtered_places = []
    if selected_categories and allowed_types_set:
        for place in places_data:
            place_types = [t.lower() for t in place.get('types', [])]
            if any(t in allowed_types_set for t in place_types):
                filtered_places.append(place)
    else:
        filtered_places = places_data
    
    print(f"DEBUG: Places after category filter: {len(filtered_places)}")
    
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
        
        print(f"DEBUG: Slot '{slot['name']}': Found {len(slot_places)} places within {max_dist if slot == time_slots[0] else max_distance_km}km")
        
        # Add variety: shuffle places within distance tiers for randomization
        # Tier 1: Very close (0-500m) - highest priority
        # Tier 2: Walkable (500m-1km) - medium priority  
        # Tier 3: Further (1km-1.5km) - lower priority
        
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
    
    print(f"DEBUG: Generated itinerary with {len(itinerary)} items")
    if len(itinerary) == 0:
        print("DEBUG: WARNING - Empty itinerary generated!")
        print(f"DEBUG: Filtered places count: {len(filtered_places)}")
        print(f"DEBUG: Time slots count: {len(time_slots)}")
    
    return Response({
        'itinerary': itinerary,
        'total_items': len(itinerary),
        'neighborhood': 'Local Area',  # Could be extracted from address
        'metadata': {'algorithm': 'rule_based'}
    }, status=status.HTTP_200_OK)

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

import uuid
from .models import PublicItinerary # Assuming PublicItinerary model can be reused for skeleton
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import date # Added this import
def _get_city_coordinates(city_name):
    """
    Fetch coordinates for a city or neighborhood using OpenStreetMap (via Photon API).
    """
    import urllib.parse
    import traceback
    try:
        # URL-encode the city name properly
        encoded_name = urllib.parse.quote(city_name)
        url = f"https://photon.komoot.io/api/?q={encoded_name}&limit=1"
        print(f"DEBUG: Geocoding URL: {url}")
        headers = {'User-Agent': 'ResBackend/1.0 (contact@example.com)'}
        response = requests.get(url, timeout=5, headers=headers)
        print(f"DEBUG: Geocoding response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG: Geocoding features count: {len(data.get('features', []))}")
            if data.get('features'):
                feature = data['features'][0]
                coords = feature['geometry']['coordinates']
                props = feature.get('properties', {})
                result_name = props.get('name', 'Unknown')
                result_city = props.get('city', props.get('county', ''))
                print(f"DEBUG: Photon returned '{result_name}' in '{result_city}' at [{coords[1]:.4f}, {coords[0]:.4f}]")
                # Photon returns [lon, lat], we need (lat, lon)
                return float(coords[1]), float(coords[0])
            else:
                print(f"WARNING: Photon returned no features for '{city_name}'")
    except Exception as e:
        print(f"ERROR: Geocoding failed for '{city_name}': {e}")
        traceback.print_exc()
        
    # Fallback to default (NYC center)
    print(f"WARNING: Using NYC fallback coordinates for '{city_name}'")
    return 40.7128, -74.0060

def _get_city_candidates(city_name, vibes):
    """Generate a pool of mock candidate places for a city to feed the solver"""
    lat, lng = _get_city_coordinates(city_name)
    candidates = []
    
    # Generate 15-20 candidates for the solver to pick from
    types = ['cafe', 'restaurant', 'park', 'museum', 'bar', 'bakery']
    categories = ['Trendy', 'Cozy', 'Vibrant', 'Upscale', 'Relaxed']
    
    for i in range(20):
        ctype = types[i % len(types)]
        vibe = categories[i % len(categories)]
        
        # Jitter coordinates within 2km
        c_lat = lat + (i * 0.002) - 0.02
        c_lng = lng + (i * 0.003) - 0.03
        
        candidates.append({
            'place_id': f"mock-p-{city_name}-{i}",
            'name': f"{city_name} {vibe} {ctype.capitalize()}",
            'rating': 4.0 + (i % 10) * 0.1,
            'types': [ctype, 'point_of_interest'],
            'categories': [ctype, vibe],
            'lat': c_lat,
            'lng': c_lng,
            'address': f"{i*123} Wander Lane, {city_name}",
            'hours': [{"day": d, "hours": "8:00 AM - 10:00 PM"} for d in range(7)]
        })
    return candidates


@api_view(['POST'])
@permission_classes([]) # Adjust permissions as needed
def create_itinerary_skeleton(request):
    """
    Creates a blank itinerary ID in Supabase and returns it.
    """
    try:
        # Ensure request.data is available (DRF handles JSON parsing)
        if not hasattr(request, 'data') or not request.data:
            return Response(
                {"error": "Invalid request body. Expected JSON data."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data
        destination = data.get('destination')
        group_size = data.get('group_size')
        vibes = data.get('vibes', [])

        # Default start_date and end_date to today if not provided
        start_date_str = data.get('start_date', date.today().isoformat())
        end_date_str = data.get('end_date', date.today().isoformat())

        if not all([destination, group_size, vibes]):
            return Response(
                {"error": "Missing required fields: destination, group_size, vibes."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Get coordinates for the destination (Now uses real OSM geocoding)
        lat, lng = _get_city_coordinates(destination)
        print(f"DEBUG: Geocoded '{destination}' to {lat},{lng}")
        
        # 2. Fetch real data from Supabase (Hybrid Strategy: PostGIS RPC + Curated Lemon8)
        from .geohash_cache import get_neighborhood_cluster_rpc, get_curated_places_from_lemon8, deduplicate_places
        
        # Always fetch curated places (the "gold standard" with rich notes)
        curated_candidates = get_curated_places_from_lemon8(lat, lng, radius_km=2.5)
        print(f"DEBUG: Found {len(curated_candidates)} curated Lemon8 places near ({lat:.4f}, {lng:.4f})")
        
        # Try the fast PostGIS RPC for a large volume of nearby spots
        cluster_candidates, rpc_success = get_neighborhood_cluster_rpc(lat, lng, radius_meters=2500)
        print(f"DEBUG: Found {len(cluster_candidates)} cluster places via RPC (success={rpc_success})")
        
        # Merge them (curated first to give them slight precedence in case of identical names)
        candidates = deduplicate_places(curated_candidates + cluster_candidates)
        print(f"DEBUG: After deduplication, total candidates = {len(candidates)}")
        
        if not candidates or len(candidates) < 5:
            # Fallback to general restaurants if pool is too small
            print(f"DEBUG: Combined pool has only {len(candidates)} places, falling back to scraped data")
            search_query = vibes[0] if vibes else "trending restaurant"
            scraped_places, _ = get_cached_or_scraped_places(lat, lng, query=search_query, radius_km=2.5)
            
            # If still nothing, try a very broad query
            if not scraped_places:
                scraped_places, _ = get_cached_or_scraped_places(lat, lng, query="restaurant", radius_km=3.0)
            
            candidates = deduplicate_places(candidates + scraped_places)

        if not candidates:
            return Response({
                'error': f'Could not find enough places near {destination} ({lat},{lng}) to generate an itinerary.',
                'status': 'error',
                'geocoded_coords': [lat, lng]
            }, status=status.HTTP_404_NOT_FOUND)

        # 3. Create a realistic itinerary using the enhanced NBASolver (Recursive Chain)
        itinerary_id = str(uuid.uuid4())
        solver = NBASolver()
        
        # Convert vibes to preferred cuisines for the solver's internal scoring
        user_prefs = {'preferred_cuisines': vibes}
        
        itinerary_data = solver.generate_full_day_itinerary(
            user_location=(lat, lng),
            start_time=datetime.now().replace(hour=9, minute=0), # Start at 9 AM
            places=candidates,
            max_steps=5, # Generate a full day
            max_distance_km=6.0, # Slightly more walking for day plans
            user_preferences=user_prefs
        )
        
        itinerary_stops = itinerary_data.get('itinerary', [])

        if not itinerary_stops:
            return Response({
                'error': 'Could not generate a valid path through the selected places.',
                'status': 'error'
            }, status=status.HTTP_404_NOT_FOUND)

        # 4. Format stops for ItineraryDetailScreen
        formatted_stops = []
        for stop in itinerary_stops:
            # Extract categories for display safely
            cat_display = stop.get('category_normalized', 'Spot').capitalize()
            bearing = stop.get('bearing', 'N')
            
            # Use the intelligent reason generated by NBASolver (truncate for UI safety)
            reason = stop.get('reason') or f"Highly rated stop in {destination}."
            if len(reason) > 160:
                reason = reason[:157] + "..."
            
            formatted_stops.append({
                "place_name": stop.get('name', 'Unknown Spot'),
                "category": f"{bearing} | {cat_display}",
                "start_time": stop.get('estimated_arrival', '10:00 AM'),
                "tip": reason,
                "photos": stop.get('photos') or ["https://images.unsplash.com/photo-1494522855154-9297ac14b55f?q=80&w=800"]
            })

        clean_vibe = vibes[0] if vibes else "Exploration"
        title = f"{destination}: {clean_vibe} Escape"
        subtitle = f"A solver-optimized journey through {destination} using real Supabase data."

        # Return the comprehensive itinerary data (compatible with ItineraryDetailScreen)
        return Response({
            'itinerary_id': itinerary_id,
            'id': itinerary_id,
            'status': 'success',
            'message': 'Itinerary generated via NBASolver.',
            'title': title,
            'subtitle': subtitle,
            'description': subtitle,
            'tags': vibes,
            'sample_image_url': 'https://images.unsplash.com/photo-1494522855154-9297ac14b55f?q=80&w=800',
            'itinerary_data': {
                'itinerary': formatted_stops,
                'route_stats': {
                    'total_distance_km': 4.2,
                    'total_duration_hours': 10
                }
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        import traceback
        print(f"ERROR: Exception in create_itinerary_skeleton: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to create itinerary skeleton: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])
def get_address_suggestions_view(request):
    """
    Returns a list of address/city suggestions for a given query.
    Used for autocomplete in the Trip Wizard.
    """
    from .suggest_service import get_address_suggestions
    query = request.GET.get('q', '')
    if not query:
        return Response([], status=status.HTTP_200_OK)
        
    suggestions = get_address_suggestions(query)
    return Response(suggestions, status=status.HTTP_200_OK)


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
    print(f"DEBUG: get_featured_itineraries() called")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Request path: {request.path}")
    print(f"DEBUG: Request GET params: {request.GET}")
    print(f"DEBUG: Request META REMOTE_ADDR: {request.META.get('REMOTE_ADDR', 'N/A')}")
    print(f"DEBUG: Request META HTTP_HOST: {request.META.get('HTTP_HOST', 'N/A')}")
    try:
        limit = int(request.GET.get('limit', 8))
        include_all = request.GET.get('include_all', 'false').lower() == 'true'
        
        # Count total featured itineraries in database
        total_featured_count = PreCreatedItinerary.objects.filter(
            is_featured=True
        ).count()
        print(f"DEBUG: Total featured itineraries in database: {total_featured_count}")
        print(f"DEBUG: Requested limit: {limit}")
        
        # Get featured itineraries
        featured = PreCreatedItinerary.objects.filter(
            is_featured=True
        ).order_by('-created_at')[:limit]
        
        print(f"DEBUG: Returning {len(featured)} featured itineraries")
        
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


@api_view(['POST'])
@permission_classes([])
def next_best_action(request):
    """
    Next Best Action (NBA) endpoint for real-time recommendations.
    
    Returns only the next 2 steps (next stop + backup) instead of full itinerary.
    Uses caching, directional filtering, and time-context to provide fast responses.
    
    Request body:
    {
        "latitude": 40.7306,
        "longitude": -73.9352,
        "heading": 0.0,  // degrees (0-360, North=0), optional
        "timestamp": "2024-01-15T13:15:00Z"  // ISO format, optional (defaults to now)
    }
    
    Response:
    {
        "next_stop": {...},
        "backup_stop": {...},
        "context": "lunch",
        "confidence": 0.85,
        "cache_hit": true,
        "response_time_ms": 45
    }
    """
    import time
    start_time = time.time()
    
    try:
        data = json.loads(request.body) if isinstance(request.body, bytes) else request.data
        
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        heading = data.get('heading')  # Optional
        timestamp_str = data.get('timestamp')
        
        # Parse timestamp or use now
        if timestamp_str:
            from datetime import datetime
            current_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            if current_time.tzinfo is None:
                from django.utils import timezone
                current_time = timezone.now()
        else:
            from django.utils import timezone
            current_time = timezone.now()
        
        # Calculate geohash and time context
        geohash = get_geohash(latitude, longitude, precision=7)
        time_context = get_time_context_label(current_time.hour)
        query_context = time_context
        
        user_preferences = data.get('user_preferences') or data.get('preferences')
        
        # Optional: radius to search for places (default 1km)
        radius_km = float(data.get('radius_km', 1.0))
        radius_meters = radius_km * 1000
        
        # --- PHASE 3: PostGIS-based Neighborhood Clustering ---
        # Try the fast PostGIS RPC first, fall back to Python filtering if unavailable
        from .geohash_cache import get_neighborhood_cluster_rpc
        
        print(f"DEBUG: Fetching neighborhood cluster for {latitude},{longitude} (radius={radius_meters}m)")
        places, rpc_success = get_neighborhood_cluster_rpc(latitude, longitude, radius_meters)
        
        if not places or not rpc_success:
            # Fallback to existing hybrid fetch (curated + scraped)
            print(f"DEBUG: RPC fallback - using get_cached_or_scraped_places")
            places, cache_hit = get_cached_or_scraped_places(latitude, longitude, query_context, radius_km=radius_km)
        else:
            cache_hit = True  # RPC is essentially a cache hit (fast DB query)

        if not places:
            return Response({
                "context": time_context,
                "confidence": 0.0,
                "summary": "No places found in this area.",
                "itinerary": [],
                "backup_option": None,
                "cache_hit": cache_hit,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "message": "No places found after fetching and merging data."
            }, status=status.HTTP_200_OK)
        
        # Apply directional filter if heading provided
        if heading is not None:
            filtered_places = filter_directional_places(
                places,
                (latitude, longitude),
                float(heading),
                cone_angle=120
            )
            # If directional filter wipes out results, fall back to original list
            if filtered_places:
                places = filtered_places
            else:
                print("DEBUG: Directional filter returned 0 places; using unfiltered set")
        
        # Optional: number of steps (default 2 for rolling horizon)
        max_steps = int(data.get('max_steps', 2))
        
        # Solve for next action
        solver = NBASolver()
        
        if max_steps > 2:
            # Recursive Chain Solver (Full Day)
            result = solver.generate_full_day_itinerary(
                user_location=(latitude, longitude),
                start_time=current_time,
                places=places,
                max_steps=max_steps
            )
        else:
            # Rolling Horizon Solver (Next 2 steps + Backup)
            result = solver.solve_next_action(
                user_location=(latitude, longitude),
                heading=float(heading) if heading is not None else None,
                current_time=current_time,
                places=places,
                user_preferences=user_preferences
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        result['cache_hit'] = cache_hit
        result['response_time_ms'] = response_time_ms
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"ERROR: NBA endpoint error: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to get next best action: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([])
def generate_itinerary(request):
    """
    Centralized API endpoint for generating full-day itineraries.
    
    Request body (accepts both formats):
    {
        "start_lat": 40.7209,  // or "latitude"
        "start_long": -74.0022,  // or "longitude"
        "selected_vibe": "romantic",  // optional, will be randomized if null
        "social_context": "couple",  // optional, defaults to "couple" if null
        "radius_meters": 3000,
        "local_time_start": "10:00"
    }
    
    Alternative format (from geocoding endpoint):
    {
        "latitude": 40.7209,
        "longitude": -74.0022,
        "base_location": "midtown",  // optional, for reference
        ...
    }
    
    Returns:
    {
        "itinerary": [
            {"slot": "coffee", "time": "10:00 AM", "place_id": "...", "name": "...", "vibe_match": 0.85},
            ...
        ],
        "hidden_gems_injected": 2,
        "total_walk_time_mins": 45,
        "narrative": "..."
    }
    """
    try:
        from .day_planner_service import DayPlannerService
        
        data = request.data
        
        # Accept both formats: start_lat/start_long or latitude/longitude (from geocoding)
        start_lat = data.get('start_lat') or data.get('latitude')
        start_long = data.get('start_long') or data.get('longitude')
        selected_vibe = data.get('selected_vibe')
        social_context = data.get('social_context')
        radius_meters = int(data.get('radius_meters', 3000))
        local_time_start = data.get('local_time_start', '10:00')
        
        # #region agent log
        import json
        import os
        log_path = r'c:\Users\PURANJAY\OneDrive\Documents\Res_2\.cursor\debug.log'
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'sessionId': 'debug-session',
                    'runId': 'run1',
                    'hypothesisId': 'A',
                    'location': 'views.py:3817',
                    'message': 'Received generate_itinerary request',
                    'data': {
                        'start_lat': start_lat,
                        'start_long': start_long,
                        'selected_vibe': selected_vibe,
                        'social_context': social_context,
                        'will_use_random_nyc': start_lat is None or start_long is None
                    },
                    'timestamp': int(__import__('time').time() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        # Apply defaults: randomize selected_vibe if null, default social_context to "couple"
        if selected_vibe is None:
            import random
            from supabase_config import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                try:
                    result = supabase.table("venue_vibes").select("vibe_slug").limit(100).execute()
                    if result.data:
                        available_vibes = list(set([v.get('vibe_slug') for v in result.data if v.get('vibe_slug')]))
                        if available_vibes:
                            selected_vibe = random.choice(available_vibes)
                            print(f"DEBUG: Randomized selected_vibe to: {selected_vibe}")
                except Exception as e:
                    print(f"Could not fetch vibes for randomization: {e}")
                    # Fallback to common vibes
                    common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                    selected_vibe = random.choice(common_vibes)
            else:
                # Fallback to common vibes
                common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                selected_vibe = random.choice(common_vibes)
        
        if social_context is None:
            social_context = 'couple'
            print(f"DEBUG: Defaulted social_context to: couple")
        
        # If coordinates are not provided, the service will use a random NYC location
        # Convert to float only if provided, otherwise pass None
        start_lat = float(start_lat) if start_lat is not None else None
        start_long = float(start_long) if start_long is not None else None
        
        # Validate social_context
        valid_contexts = ['couple', 'solo', 'group', 'family']
        if social_context not in valid_contexts:
            return Response(
                {"error": f"social_context must be one of: {', '.join(valid_contexts)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract cuisine preferences from request
        cuisine_preferences = data.get('cuisine_preferences')
        cuisine_preference_min = data.get('cuisine_preference_min')
        cuisine_preference_max = data.get('cuisine_preference_max')
        
        print(f"DEBUG: Received cuisine_preferences: {cuisine_preferences}")
        print(f"DEBUG: Received cuisine_preference_min: {cuisine_preference_min}")
        print(f"DEBUG: Received cuisine_preference_max: {cuisine_preference_max}")
        
        # Generate itinerary
        planner = DayPlannerService()
        result = planner.generate_itinerary(
            start_lat=start_lat,
            start_long=start_long,
            selected_vibe=selected_vibe,
            social_context=social_context,
            radius_meters=radius_meters,
            local_time_start=local_time_start,
            cuisine_preferences=cuisine_preferences,
            cuisine_preference_min=cuisine_preference_min,
            cuisine_preference_max=cuisine_preference_max
        )
        
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"ERROR: generate_itinerary endpoint error: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to generate itinerary: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([])
def itinerary_details(request):
    """
    Fetch full venue details for place_ids returned from generate-itinerary.
    
    Request body:
    {
        "place_ids": ["ChIJeVu4h9hbwokRxYUvKBeI738", "ChIJdVqFHRVbwokRtqzlk7CRCb0"]
    }
    
    Returns:
    {
        "venues": [
            {
                "place_id": "...",
                "name": "...",
                "address": "...",
                "photos": [...],
                "hours": [...],
                "rating": 4.8,
                "insights": {...}
            },
            ...
        ]
    }
    """
    try:
        from .day_planner_service import DayPlannerService
        
        data = request.data
        place_ids = data.get('place_ids', [])
        
        if not place_ids:
            return Response(
                {"error": "place_ids array is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(place_ids, list):
            return Response(
                {"error": "place_ids must be an array"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Limit to reasonable number
        if len(place_ids) > 20:
            return Response(
                {"error": "Maximum 20 place_ids allowed per request"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Fetch venue details
        planner = DayPlannerService()
        venues = planner.get_venue_details(place_ids)
        
        return Response(
            {"venues": venues},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        import traceback
        print(f"ERROR: itinerary_details endpoint error: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to fetch venue details: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([])
def geocode_location(request):
    """
    Geocode a location hint (neighborhood, city) to coordinates with non-deterministic randomization.
    
    Each call returns different coordinates within the location for variety.
    
    Request body:
    {
        "location_hint": "DUMBO"
    }
    
    Returns:
    {
        "latitude": 40.7033,
        "longitude": -73.9881,
        "base_location": "DUMBO, Brooklyn"
    }
    """
    try:
        from .geocoding_service import geocode_with_randomization, is_within_nyc_bounds
        
        location_hint = request.data.get('location_hint', '')
        if not location_hint:
            return Response(
                {"error": "location_hint is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lat, lng = geocode_with_randomization(location_hint)
        
        # Verify coordinates are within NYC bounds (should always be true after our update)
        if not is_within_nyc_bounds(lat, lng):
            print(f"WARNING: Geocoded coordinates ({lat}, {lng}) are outside NYC bounds for '{location_hint}'")
            # This shouldn't happen with our updated geocoding service, but log it if it does
        
        return Response({
            "latitude": lat,
            "longitude": lng,
            "base_location": location_hint
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"ERROR: geocode_location endpoint error: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to geocode location: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([])
def parse_query(request):
    """
    Parse natural language query using LLM to extract structured parameters.
    
    Request body:
    {
        "query": "romantic dinner date in SoHo",
        "user_location": {"lat": 40.7209, "lng": -74.0022}  // optional
    }
    
    Returns:
    {
        "selected_vibe": "romantic",
        "social_context": "couple",
        "location_hint": "SoHo",
        "time_preference": "evening",
        "parsed_intent": "..."
    }
    """
    try:
        import requests
        from django.conf import settings
        from decouple import config
        
        query = request.data.get('query', '')
        if not query:
            return Response(
                {"error": "query is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        api_key = (getattr(settings, 'OPENROUTER_API_KEYv3', '') or 
                  config('OPENROUTER_API_KEYv3', default='') or
                  getattr(settings, 'OPENROUTER_API_KEY', '') or 
                  config('OPENROUTER_API_KEY', default=''))
        model = config('OPENROUTER_CHAT_MODEL', default='xiaomi/mimo-v2-flash:free')
        
        # Get available vibe slugs from venue_vibes table
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        vibe_slugs = [
            "romantic", "dinner_date", "speakeasy", "fine_dining",
            "solo_date", "work_friendly", "coffee", "coffee_run",
            "dinner_group", "brunch_buzzy", "casual_lunch",
            "breakfast_classic", "family_friendly", "late_night_eats",
            "art_house", "new_american_aesthetic", "australian_cafe_aesthetic",
            "italian_red_sauce_aesthetic", "natural_wine", "pizza_nyc_aesthetic",
            "french_bistro_aesthetic", "japanese_izakaya_aesthetic", "korean_pocha_aesthetic"
        ]
        
        # Try to get more vibes from database (optional enhancement)
        if supabase:
            try:
                # Get a sample of distinct vibe slugs
                result = supabase.table("venue_vibes").select("vibe_slug").limit(100).execute()
                if result.data:
                    db_vibes = list(set([v.get('vibe_slug') for v in result.data if v.get('vibe_slug')]))
                    vibe_slugs.extend(db_vibes[:30])  # Add up to 30 more
                    vibe_slugs = list(set(vibe_slugs))  # Remove duplicates
            except Exception as e:
                print(f"Could not fetch vibes from DB: {e}")
                # Use default list above
        
        system_prompt = f"""You are a query parser for a day planner app. Extract structured parameters from natural language queries.

Available vibe slugs: {', '.join(vibe_slugs[:30])}

IMPORTANT VIBE MAPPING RULES:
- "romantic", "date night", "date", "romantic dinner" → "dinner_date" (NOT speakeasy, NOT romantic)
- "speakeasy", "hidden bar", "cocktail bar" → "speakeasy"
- "coffee", "cafe", "morning coffee" → "coffee" or "coffee_run"
- "brunch", "breakfast" → "brunch_buzzy" or "breakfast_classic"
- "fine dining", "upscale", "fancy" → "fine_dining"
- "solo", "alone", "work" → "solo_date" or "work_friendly"

Extract and return ONLY valid JSON with these fields:
- selected_vibe: vibe_slug that best matches the query (or null)
- social_context: "couple", "solo", "group", or "family" (or null)
- location_hint: neighborhood or area mentioned (or null)
- time_preference: "morning", "afternoon", "evening", "night" (or null)
- parsed_intent: brief summary of what user wants

Examples:
Query: "romantic dinner date"
{{"selected_vibe": "dinner_date", "social_context": "couple", "time_preference": "evening", "parsed_intent": "Romantic dinner date"}}

Query: "romantic date night"
{{"selected_vibe": "dinner_date", "social_context": "couple", "time_preference": "evening", "parsed_intent": "Romantic date night"}}

Query: "solo coffee morning"
{{"selected_vibe": "coffee", "social_context": "solo", "time_preference": "morning", "parsed_intent": "Solo coffee morning"}}

Query: "family brunch"
{{"selected_vibe": "brunch_buzzy", "social_context": "family", "time_preference": "morning", "parsed_intent": "Family brunch"}}

Return ONLY the JSON object, no markdown, no explanations."""
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.3,
                },
                timeout=10
            )
            response.raise_for_status()
            llm_response = response.json()['choices'][0]['message']['content'].strip()
            
            # Clean up markdown if present
            if llm_response.startswith("```json"):
                llm_response = llm_response.split("```json")[1].split("```")[0].strip()
            elif llm_response.startswith("```"):
                llm_response = llm_response.split("```")[1].split("```")[0].strip()
            
            import json
            parsed = json.loads(llm_response)
            
            # Apply defaults: randomize selected_vibe if null, default social_context to "couple"
            if parsed.get('selected_vibe') is None:
                # Get random vibe from available vibes
                import random
                if supabase:
                    try:
                        result = supabase.table("venue_vibes").select("vibe_slug").limit(100).execute()
                        if result.data:
                            available_vibes = list(set([v.get('vibe_slug') for v in result.data if v.get('vibe_slug')]))
                            if available_vibes:
                                parsed['selected_vibe'] = random.choice(available_vibes)
                                print(f"DEBUG: Randomized selected_vibe to: {parsed['selected_vibe']}")
                    except Exception as e:
                        print(f"Could not fetch vibes for randomization: {e}")
                        # Fallback to common vibes
                        common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                        parsed['selected_vibe'] = random.choice(common_vibes)
                else:
                    # Fallback to common vibes
                    common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                    parsed['selected_vibe'] = random.choice(common_vibes)
            
            if parsed.get('social_context') is None:
                parsed['social_context'] = "couple"
                print(f"DEBUG: Defaulted social_context to: couple")
            
            return Response(parsed, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            # Fallback: simple keyword matching
            query_lower = query.lower()
            result = {
                "selected_vibe": None,
                "social_context": None,
                "location_hint": None,
                "time_preference": None,
                "parsed_intent": query
            }
            
            # Simple vibe matching - map "romantic" to "dinner_date" (valid vibe_slug)
            if any(word in query_lower for word in ["romantic", "romance", "date", "dinner date", "date night"]):
                result["selected_vibe"] = "dinner_date"  # Use valid vibe_slug
                result["social_context"] = "couple"
            elif any(word in query_lower for word in ["solo", "alone", "myself"]):
                result["social_context"] = "solo"
            elif any(word in query_lower for word in ["coffee", "cafe", "morning"]):
                result["selected_vibe"] = "coffee"
                result["time_preference"] = "morning"
            elif any(word in query_lower for word in ["brunch", "breakfast"]):
                result["selected_vibe"] = "brunch_buzzy"
                result["time_preference"] = "morning"
            elif any(word in query_lower for word in ["group", "friends", "party"]):
                result["social_context"] = "group"
            
            # Time preference
            if any(word in query_lower for word in ["morning", "breakfast", "coffee"]):
                result["time_preference"] = "morning"
            elif any(word in query_lower for word in ["afternoon", "lunch"]):
                result["time_preference"] = "afternoon"
            elif any(word in query_lower for word in ["evening", "dinner", "night"]):
                result["time_preference"] = "evening"
            
            # Apply defaults: randomize selected_vibe if null, default social_context to "couple"
            if result.get("selected_vibe") is None:
                import random
                from supabase_config import get_supabase_client
                supabase = get_supabase_client()
                if supabase:
                    try:
                        vibe_result = supabase.table("venue_vibes").select("vibe_slug").limit(100).execute()
                        if vibe_result.data:
                            available_vibes = list(set([v.get('vibe_slug') for v in vibe_result.data if v.get('vibe_slug')]))
                            if available_vibes:
                                result["selected_vibe"] = random.choice(available_vibes)
                                print(f"DEBUG: Randomized selected_vibe to: {result['selected_vibe']}")
                    except Exception as e:
                        print(f"Could not fetch vibes for randomization: {e}")
                        # Fallback to common vibes
                        common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                        result["selected_vibe"] = random.choice(common_vibes)
                else:
                    # Fallback to common vibes
                    common_vibes = ["dinner_date", "coffee", "brunch_buzzy", "casual_lunch", "solo_date", "work_friendly"]
                    result["selected_vibe"] = random.choice(common_vibes)
            
            if result.get("social_context") is None:
                result["social_context"] = "couple"
                print(f"DEBUG: Defaulted social_context to: couple")
            
            return Response(result, status=status.HTTP_200_OK)
            
    except Exception as e:
        import traceback
        print(f"ERROR: parse_query endpoint error: {str(e)}")
        print(f"ERROR: {traceback.format_exc()}")
        return Response(
            {"error": f"Failed to parse query: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )