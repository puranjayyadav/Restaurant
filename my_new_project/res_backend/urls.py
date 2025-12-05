from django.urls import path, include
from .views import (
    verify_token, get_trips, EstablishmentViewSet, get_trip_recommendations, 
    get_similar_restaurants, record_user_interaction, create_session, 
    get_personalized_recommendations, generate_day_itinerary,
    submit_public_itinerary, get_public_itineraries, like_public_itinerary,
    add_public_itinerary_to_schedule, share_public_itinerary, update_public_itinerary,
    delete_public_itinerary, approve_public_itinerary, get_user_stats,
    get_scraped_restaurants, get_scraped_restaurant_detail, create_scraped_restaurant,
    generate_and_enrich_itinerary, get_pre_created_itineraries, 
    pre_create_itineraries, get_featured_itineraries, get_pre_created_itinerary_detail
)
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
    # Public Itinerary Sharing endpoints
    path('submit-itinerary/', submit_public_itinerary, name='submit-itinerary'),
    path('public-itineraries/', get_public_itineraries, name='public-itineraries'),
    path('public-itineraries/<str:itinerary_id>/like/', like_public_itinerary, name='like-itinerary'),
    path('public-itineraries/<str:itinerary_id>/add-to-schedule/', add_public_itinerary_to_schedule, name='add-to-schedule'),
    path('public-itineraries/<str:itinerary_id>/share/', share_public_itinerary, name='share-itinerary'),
    path('public-itineraries/<str:itinerary_id>/', update_public_itinerary, name='update-itinerary'),
    path('public-itineraries/<str:itinerary_id>/delete/', delete_public_itinerary, name='delete-itinerary'),
    path('admin/approve-itinerary/<str:itinerary_id>/', approve_public_itinerary, name='approve-itinerary'),
    path('user-stats/<str:user_id>/', get_user_stats, name='user-stats'),
    # Scraped Restaurant endpoints
    path('scraped-restaurants/', get_scraped_restaurants, name='scraped-restaurants'),
    path('scraped-restaurants/<int:restaurant_id>/', get_scraped_restaurant_detail, name='scraped-restaurant-detail'),
    path('scraped-restaurants/create/', create_scraped_restaurant, name='create-scraped-restaurant'),
    # Discovery & Pre-Created Itineraries endpoints
    path('discovery/generate-and-enrich-itinerary/', generate_and_enrich_itinerary, name='generate-and-enrich-itinerary'),
    path('discovery/pre-created-itineraries/', get_pre_created_itineraries, name='pre-created-itineraries'),
    path('discovery/pre-created-itineraries/<int:itinerary_id>/', get_pre_created_itinerary_detail, name='pre-created-itinerary-detail'),
    path('discovery/pre-create-itineraries/', pre_create_itineraries, name='pre-create-itineraries'),
    path('discovery/featured-itineraries/', get_featured_itineraries, name='featured-itineraries'),
]
