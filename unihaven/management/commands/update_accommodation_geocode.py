from django.core.management.base import BaseCommand, CommandError
from unihaven.models import Accommodation
from django.core.exceptions import ObjectDoesNotExist
from unihaven.utils.geocoding import geocode_address

class Command(BaseCommand):
    help = 'Update accommodation with geocoding information (latitude, longitude, and geo_address)'

    def add_arguments(self, parser):
        parser.add_argument('accommodation_id', type=int, help='ID of the accommodation to update')
        parser.add_argument('--use_api', action='store_true', help='Use geocoding API to update coordinates automatically')
        parser.add_argument('--latitude', type=float, required=False, help='Manual latitude coordinate')
        parser.add_argument('--longitude', type=float, required=False, help='Manual longitude coordinate')
        parser.add_argument('--geo_address', type=str, required=False, help='Manual geo address')

    def handle(self, *args, **options):
        try:
            # Get accommodation by ID
            try:
                accommodation = Accommodation.objects.get(id=options['accommodation_id'])
            except ObjectDoesNotExist:
                raise CommandError(f'Accommodation with ID {options["accommodation_id"]} does not exist')
            
            if options.get('use_api'):
                # Use the API to geocode the address
                self.stdout.write(f'Attempting to geocode address: {accommodation.address}')
                success = accommodation.update_geocoding()
                
                if success:
                    self.stdout.write(self.style.SUCCESS(
                        f'Successfully geocoded address for accommodation {accommodation.id}'
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        'Geocoding failed or is not yet implemented.'
                    ))
            else:
                # Use manually provided coordinates
                if options.get('latitude') is not None:
                    accommodation.latitude = options['latitude']
                
                if options.get('longitude') is not None:
                    accommodation.longitude = options['longitude']
                
                if options.get('geo_address'):
                    accommodation.geo_address = options['geo_address']
                
                accommodation.save()
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully updated geocoding information for accommodation {accommodation.id}'
                ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating accommodation geocode: {str(e)}')) 