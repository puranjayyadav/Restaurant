# views.py
from rest_framework.decorators import api_view
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

# Path to your service account key JSON file
SERVICE_ACCOUNT_PATH = '../creds/restaurant-47dab-firebase-adminsdk-fbsvc-a2225a7d82.json'

# Initialize Firebase app (if not already initialized)
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

# Get a Firestore client
db = firestore.client()

@api_view(['POST'])
def verify_token(request):
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
        # 2. Verify the token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token.get('uid', None)
        if not uid:
            return Response({"error": "No UID in token"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({"message": "Token is valid", "uid": uid}, 
                        status=status.HTTP_200_OK)
    except auth.ExpiredIdTokenError:
        return Response({"error": "Token is expired"}, 
                        status=status.HTTP_401_UNAUTHORIZED)
    except auth.InvalidIdTokenError:
        return Response({"error": "Invalid token"}, 
                        status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({"error": str(e)}, 
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