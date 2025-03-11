from django.urls import path
from django.urls import path
from .views import verify_token,get_trips

urlpatterns = [
    path('verify-token/', verify_token, name='verify_token'),
    path('get-trips/', get_trips, name='get_trips'),
    #path('create_session/', create_session,name='create_session')
]
