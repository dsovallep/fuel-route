import logging
from django.core.management.base import BaseCommand
from api.geocoding import update_fuel_station_coordinates 

class Command(BaseCommand):
    help = 'Updates coordinates for FuelStation instances'

    def handle(self, *args, **options):
        
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        self.stdout.write("Starting coordinate update process...")
        update_fuel_station_coordinates()
        self.stdout.write(self.style.SUCCESS('Coordinate update process completed. Check logs for details.'))