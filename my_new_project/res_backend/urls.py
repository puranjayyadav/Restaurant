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
    pre_create_itineraries, get_featured_itineraries, get_pre_created_itinerary_detail,
    next_best_action, create_itinerary_skeleton, get_address_suggestions_view,
    get_hotspot_itinerary, generate_itinerary, itinerary_details, parse_query, geocode_location,
    search_venues, save_itinerary, get_saved_itineraries, mark_venue_interaction, delete_venue_interaction,
    lemon8_rag_search
)
from .density_heatmap import get_density_heatmap
try:
    from . import lemon8_api
except ImportError:
    lemon8_api = None
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("lemon8_api module not found - Lemon8 endpoints will be disabled")
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'establishments', EstablishmentViewSet, basename='establishment')

urlpatterns = [
    path('verify-token/', verify_token, name='verify_token'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/trips/', get_trips, name='get_trips'),
    path('api/trip-recommendations/', get_trip_recommendations, name='get_trip_recommendations'),
    path('api/similar-restaurants/', get_similar_restaurants, name='get_similar_restaurants'),
    path('api/record-interaction/', record_user_interaction, name='record_user_interaction'),
    path('api/create-session/', create_session, name='create_session'),
    path('api/personalized-recommendations/', get_personalized_recommendations, name='get_personalized_recommendations'),
    path('api/generate-day-itinerary/', generate_day_itinerary, name='generate_day_itinerary'),
    path('api/submit-public-itinerary/', submit_public_itinerary, name='submit_public_itinerary'),
    path('api/public-itineraries/', get_public_itineraries, name='get_public_itineraries'),
    path('api/like-public-itinerary/', like_public_itinerary, name='like_public_itinerary'),
    path('api/add-public-itinerary-to-schedule/', add_public_itinerary_to_schedule, name='add_public_itinerary_to_schedule'),
    path('api/share-public-itinerary/', share_public_itinerary, name='share_public_itinerary'),
    path('api/update-public-itinerary/', update_public_itinerary, name='update_public_itinerary'),
    path('api/delete-public-itinerary/', delete_public_itinerary, name='delete_public_itinerary'),
    path('api/approve-public-itinerary/', approve_public_itinerary, name='approve_public_itinerary'),
    path('api/user-stats/', get_user_stats, name='get_user_stats'),
    path('api/scraped-restaurants/', get_scraped_restaurants, name='get_scraped_restaurants'),
    path('api/scraped-restaurant-detail/', get_scraped_restaurant_detail, name='get_scraped_restaurant_detail'),
    path('api/create-scraped-restaurant/', create_scraped_restaurant, name='create_scraped_restaurant'),
    path('api/generate-and-enrich-itinerary/', generate_and_enrich_itinerary, name='generate_and_enrich_itinerary'),
    path('api/pre-created-itineraries/', get_pre_created_itineraries, name='get_pre_created_itineraries'),
    path('api/pre-create-itineraries/', pre_create_itineraries, name='pre_create_itineraries'),
    path('api/featured-itineraries/', get_featured_itineraries, name='get_featured_itineraries'),
    path('api/pre-created-itinerary-detail/', get_pre_created_itinerary_detail, name='get_pre_created_itinerary_detail'),
    path('api/next-best-action/', next_best_action, name='next_best_action'),
    path('api/create-itinerary-skeleton/', create_itinerary_skeleton, name='create_itinerary_skeleton'),
    path('api/get-address-suggestions/', get_address_suggestions_view, name='get_address_suggestions_view'),
    path('api/get-hotspot-itinerary/', get_hotspot_itinerary, name='get_hotspot_itinerary'),
    path('api/generate-itinerary/', generate_itinerary, name='api-generate-itinerary'),
    path('api/itinerary-details/', itinerary_details, name='api-itinerary-details'),
    path('api/parse-query/', parse_query, name='api-parse-query'),
    path('api/geocode-location/', geocode_location, name='api-geocode-location'),
    path('search-venues/', search_venues, name='api-search-venues'),
    # Saved Itineraries endpoints
    path('api/save-itinerary/', save_itinerary, name='api-save-itinerary'),
    path('api/saved-itineraries/', get_saved_itineraries, name='api-saved-itineraries'),
    # User History endpoints
    path('api/mark-venue-interaction/', mark_venue_interaction, name='api-mark-venue-interaction'),
    path('api/delete-venue-interaction/', delete_venue_interaction, name='api-delete-venue-interaction'),
    path('api/rag/lemon8/search/', lemon8_rag_search, name='api-lemon8-rag-search'),
]
