from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from geopy.distance import geodesic
import requests

from .models import FuelStation
from .serializer import FuelStationSerializer


@api_view(['GET'])
def get_stations(request):
    """
    Retrieve the first 10 fuel stations from the database.

    Args:
        request: The HTTP request object.

    Returns:
        Response: A JSON response containing the serialized fuel stations.
    """
    stations = FuelStation.objects.all()
    serializer = FuelStationSerializer(stations, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def create_station(request):
    """
    Create a new fuel station.

    Args:
        request: The HTTP request object with fuel station data.

    Returns:
        Response: A JSON response with the created station data or errors.
    """
    serializer = FuelStationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def optimized_route(request):
    """
    Optimize a route by calculating the optimal fuel stops and total trip cost.

    Args:
        request: The HTTP request object containing origin and destination.

    Returns:
        JsonResponse: A JSON response with the route, optimal stops, 
        total distance, and total cost or an error message.
    """
    if request.method == 'POST':
        origin = request.POST.get('origin')
        destination = request.POST.get('destination')

        if not origin or not destination:
            return JsonResponse({'error': 'Both origin and destination are required.'}, status=400)

        route_data = get_route(settings.GOOGLE_MAPS_API_KEY, origin, destination)

        if route_data and 'routes' in route_data and route_data['routes']:
            total_distance = process_route_data(route_data)
            optimal_stops = calculate_optimal_stops(total_distance, route_data)

            total_cost = calculate_total_cost(optimal_stops)

            return JsonResponse({
                'route': route_data,
                'optimal_stops': optimal_stops,
                'total_distance': total_distance,
                'total_cost': total_cost
            })
        else:
            return JsonResponse({'error': 'Failed to retrieve route from Google Maps.'}, status=400)

    return render(request, 'route_optimizer.html', {'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY})


def get_route(api_key, origin, destination):
    """
    Fetch the driving route from Google Maps API.

    Args:
        api_key: The Google Maps API key.
        origin: The starting point of the route.
        destination: The endpoint of the route.

    Returns:
        dict: The JSON response from Google Maps API containing route data, or None if an error occurs.
    """
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'OK':
            return data
        else:
            print(f"Google Maps API Error: {data.get('status')}, {data.get('error_message', 'No error message')}")
            return None
    else:
        print(f"Error fetching route: {response.status_code}, {response.text}")
    return None


def process_route_data(route_data):
    """
    Process the route data to calculate the total distance.

    Args:
        route_data: The route data from Google Maps API.

    Returns:
        float: The total distance of the route in miles.
    """
    if not route_data.get('routes'):
        return 0
    legs = route_data['routes'][0].get('legs', [])
    total_distance = sum(leg['distance']['value'] for leg in legs)
    return total_distance / 1609.34  # Convert meters to miles


def calculate_optimal_stops(total_distance, route_data):
    """
    Calculate optimal fuel stops along the route.

    Args:
        total_distance: The total distance of the route in miles.
        route_data: The route data from Google Maps API.

    Returns:
        list: A list of dictionaries containing optimal stops and their distances.
    """
    legs = route_data['routes'][0].get('legs', [])
    if not legs:
        return []
    steps = legs[0].get('steps', [])
    current_distance = 0
    stops = []

    for step in steps:
        step_distance = step['distance']['value'] / 1609.34  # Convert meters to miles
        current_distance += step_distance

        if current_distance >= 450:  # Look for a station when ~50 miles of fuel is left
            lat, lng = step['end_location']['lat'], step['end_location']['lng']
            best_station = find_best_station(lat, lng)
            if best_station:
                stops.append({
                    'station': best_station, # The gas station found
                    'distance': current_distance # The distance traveled to that stop
                })
                current_distance = 0  # Reset distance after finding a stop
            else:
                print("Warning: No station found near the route step.")

    return stops


def find_best_station(lat, lng):
    """
    Find the best fuel station near the given coordinates.

    Args:
        lat: Latitude of the step location.
        lng: Longitude of the step location.

    Returns:
        dict: A dictionary containing the best station's name, address, price, and coordinates,
              or None if no station is found.
    """
    stations = FuelStation.objects.filter(latitude__isnull=False, longitude__isnull=False)

    if not stations.exists():
        return None  # No station found

    best_station = min(
        stations,
        key=lambda s: (
            geodesic((lat, lng), (s.latitude, s.longitude)).miles,  # Distance to the station
            s.retail_price  # Price of the fuel
        )
    )
    return {
        'name': best_station.name,
        'address': best_station.address,
        'price': float(best_station.retail_price),
        'lat': float(best_station.latitude),
        'lng': float(best_station.longitude)
    }


def calculate_total_cost(stops, mpg=10):
    """
    Calculate the total cost of fuel for the trip based on the stops.

    Args:
        stops: A list of optimal stops with fuel station information.
        mpg: Miles per gallon for the vehicle (default is 10 MPG).

    Returns:
        float: The total cost of fuel for the trip, rounded to 2 decimal places.
    """
    total_cost = 0
    for i, stop in enumerate(stops):
        if i == 0:
            distance = stop['distance']
        else:
            distance = stop['distance'] - stops[i - 1]['distance']

        gallons_needed = distance / mpg  # Calculate gallons needed for the segment
        total_cost += gallons_needed * stop['station']['price']  # Calculate cost for this segment

    return round(total_cost, 2)
