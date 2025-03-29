from django.core.management.base import BaseCommand, CommandError
from unihaven.models import Accommodation, PropertyOwner
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from decimal import Decimal
from unihaven.utils.geocoding import geocode_address

class Command(BaseCommand):
    help = 'Add a new accommodation'

    def add_arguments(self, parser):
        # Accommodation details
        parser.add_argument('--type', type=str, required=True, choices=[t[0] for t in Accommodation.TYPE_CHOICES])
        parser.add_argument('--address', type=str, required=True)
        parser.add_argument('--auto_geocode', action='store_true', help='Attempt to automatically geocode the address')
        parser.add_argument('--latitude', type=float, required=False, help='Manual latitude coordinate')
        parser.add_argument('--longitude', type=float, required=False, help='Manual longitude coordinate')
        parser.add_argument('--geo_address', type=str, required=False, help='Manual geo address')
        parser.add_argument('--available_from', type=str, required=True)
        parser.add_argument('--available_until', type=str, required=True)
        parser.add_argument('--beds', type=int, required=True)
        parser.add_argument('--bedrooms', type=int, required=True)
        parser.add_argument('--rating', type=float, required=True)
        parser.add_argument('--daily_price', type=float, required=True)
        
        # Owner details - either provide an owner_id or new owner details
        parser.add_argument('--owner_id', type=int, help='ID of existing property owner')
        parser.add_argument('--owner_name', type=str, help='Name for new property owner')
        parser.add_argument('--owner_contact', type=str, help='Contact info for new property owner')

    def handle(self, *args, **options):
        try:
            # Parse dates
            try:
                available_from = datetime.strptime(options['available_from'], '%Y-%m-%d').date()
                available_until = datetime.strptime(options['available_until'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Date format should be YYYY-MM-DD')
            
            # Check date logic
            if available_until <= available_from:
                raise CommandError('Available until date must be after available from date')
            
            # Handle owner - either use existing or create new
            if options['owner_id']:
                try:
                    owner = PropertyOwner.objects.get(id=options['owner_id'])
                except ObjectDoesNotExist:
                    raise CommandError(f'Property owner with ID {options["owner_id"]} does not exist')
            elif options['owner_name'] and options['owner_contact']:
                owner = PropertyOwner.objects.create(
                    name=options['owner_name'],
                    contact_info=options['owner_contact']
                )
                self.stdout.write(self.style.SUCCESS(f'Created new property owner with ID: {owner.id}'))
            else:
                raise CommandError('Either --owner_id or both --owner_name and --owner_contact must be provided')
            
            # Handle geocoding
            latitude = options.get('latitude')
            longitude = options.get('longitude')
            geo_address = options.get('geo_address')
            
            # If auto_geocode is enabled, try to geocode the address
            if options.get('auto_geocode'):
                self.stdout.write('Attempting to geocode address...')
                lat, lng, geo = geocode_address(options['address'])
                
                # Only update values if geocoding returned something
                if lat is not None and lng is not None and geo is not None:
                    latitude = lat
                    longitude = lng
                    geo_address = geo
                    self.stdout.write(self.style.SUCCESS('Address successfully geocoded.'))
                else:
                    self.stdout.write(self.style.WARNING('Geocoding failed or is not yet implemented.'))
            
            # Create the accommodation
            accommodation = Accommodation.objects.create(
                type=options['type'],
                address=options['address'],
                latitude=latitude,
                longitude=longitude,
                geo_address=geo_address,
                available_from=available_from,
                available_until=available_until,
                beds=options['beds'],
                bedrooms=options['bedrooms'],
                rating=options['rating'],
                daily_price=Decimal(str(options['daily_price'])),
                owner=owner
            )
            
            self.stdout.write(self.style.SUCCESS(f'Successfully added accommodation with ID: {accommodation.id}'))
            
            # Add a note about missing geocoding information
            if accommodation.latitude is None or accommodation.longitude is None or accommodation.geo_address is None:
                self.stdout.write(self.style.WARNING(
                    'Note: Geocoding information is incomplete. Use update_accommodation_geocode command to populate later.'
                ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error adding accommodation: {str(e)}')) 