from django.urls import path
from .views import verify_token, get_trips, EstablishmentViewSet
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
    #path('create_session/', create_session,name='create_session')
] + router.urls
