import csv
from django.core.management.base import BaseCommand
from api.models import FuelStation 

class Command(BaseCommand):
    help = 'Import Fuel Stations from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The CSV file to be imported')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)

            for row in reader:
                _, created = FuelStation.objects.get_or_create(
                    opis_id=row[0],
                    name=row[1],
                    address=row[2],
                    city=row[3],
                    state=row[4],
                    rack_id=row[5],
                    retail_price=row[6],
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f'Successfully imported {row[1]}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Fuel Station {row[1]} already exists'))
