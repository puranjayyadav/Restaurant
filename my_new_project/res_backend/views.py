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

# Path to your service account key JSON file
SERVICE_ACCOUNT_PATH = '../creds/restaurant-47dab-firebase-adminsdk-fbsvc-a2225a7d82.json'

# Initialize Firebase app (if not already initialized)
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
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