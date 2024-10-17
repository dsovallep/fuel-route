from django.urls import path
from .views import get_stations, create_station, optimized_route

urlpatterns = [
    path('fuelstations/', get_stations, name='get_stations'),
    path('fuelstation/create/', create_station, name='create_station'),
    path('optimized_route/', optimized_route, name='optimized_route'),
]



