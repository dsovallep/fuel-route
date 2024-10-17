import requests
from django.db import transaction
from api.models import FuelStation 
import time
import logging
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY = "AIzaSyDkrk7VifS-ljsDDmaIfc64YizN1pxgYiE" 

logger = logging.getLogger(__name__)

def geocode_address(name, address, city, state):
    params = {
        "key": API_KEY,
        "address": f"{name},{address}, {city}, {state}",
        "region": "us"
    }
    
    try:
        response = requests.get(GEOCODE_API_URL, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()
        
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return (location['lat'], location['lng'])
        else:
            logger.warning(f"Geocoding failed for {name}, {address}, {city}, {state}. Status: {data['status']}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {name}, {address}, {city}, {state}: {str(e)}")
        return None

def update_fuel_station_coordinates(batch_size=50, sleep_time=1):
    fuel_stations = FuelStation.objects.filter(latitude__isnull=True, longitude__isnull=True)
    total_count = fuel_stations.count()
    updated_count = 0
    failed_count = 0

    for i, station in enumerate(fuel_stations, 1):
        coordinates = geocode_address(station.name, station.address, station.city, station.state)
        if coordinates:
            station.latitude, station.longitude = coordinates
            try:
                station.save()
                updated_count += 1
                logger.info(f"Updated coordinates for {station.name}: Lat {station.latitude}, Long {station.longitude}")
            except Exception as e:
                logger.error(f"Failed to save coordinates for {station.name}: {str(e)}")
                failed_count += 1
        else:
            failed_count += 1

        # Commit changes every batch_size records or at the end
        if i % batch_size == 0 or i == total_count:
            try:
                transaction.commit()
                logger.info(f"Committed changes for batch ending at record {i}")
            except Exception as e:
                logger.error(f"Failed to commit batch ending at record {i}: {str(e)}")
                transaction.rollback()

        # Sleep to avoid hitting API rate limits
        time.sleep(sleep_time)

    logger.info(f"Process completed. Updated: {updated_count}, Failed: {failed_count}, Total: {total_count}")
