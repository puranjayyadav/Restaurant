from django.urls import path, include
from .views import verify_token, get_trips, EstablishmentViewSet, get_trip_recommendations, get_similar_restaurants, record_user_interaction, create_session, get_personalized_recommendations, generate_day_itinerary
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'establishments', EstablishmentViewSet, basename='establishment')

urlpatterns = [
    path('verify-token/', verify_token, name='verify_token'),
    path('get-trips/', get_trips, name='get_trips'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('create_session/', create_session, name='create_session'),
    path('', include(router.urls)),
    # Recommendation system endpoints
    path('trip/<int:trip_id>/recommendations/', get_trip_recommendations, name='trip-recommendations'),
    path('establishment/<int:establishment_id>/similar/', get_similar_restaurants, name='similar-restaurants'),
    path('interaction/', record_user_interaction, name='record-interaction'),
    path('recommendations/', get_personalized_recommendations, name='personalized-recommendations'),
    path('generate-day-itinerary/', generate_day_itinerary, name='generate-day-itinerary'),
]
