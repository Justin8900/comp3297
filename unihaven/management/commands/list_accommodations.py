from django.core.management.base import BaseCommand
from unihaven.models import Accommodation
from django.db.models import Q
from datetime import datetime

class Command(BaseCommand):
    help = 'List and view all accommodations in the database'

    def add_arguments(self, parser):
        # Optional filtering arguments
        parser.add_argument('--id', type=int, help='Filter by accommodation ID')
        parser.add_argument('--type', type=str, help='Filter by accommodation type')
        parser.add_argument('--owner_id', type=int, help='Filter by owner ID')
        parser.add_argument('--available_now', action='store_true', help='Only show accommodations available today')
        parser.add_argument('--min_price', type=float, help='Minimum daily price')
        parser.add_argument('--max_price', type=float, help='Maximum daily price')
        parser.add_argument('--min_rating', type=float, help='Minimum rating')
        parser.add_argument('--min_beds', type=int, help='Minimum number of beds')
        parser.add_argument('--address_contains', type=str, help='Address contains this string')
        parser.add_argument('--detailed', action='store_true', help='Show detailed information for each accommodation')

    def handle(self, *args, **options):
        # Start with all accommodations
        accommodations = Accommodation.objects.all().select_related('owner')
        
        # Apply filters if provided
        if options['id']:
            accommodations = accommodations.filter(id=options['id'])
        
        if options['type']:
            accommodations = accommodations.filter(type=options['type'])
        
        if options['owner_id']:
            accommodations = accommodations.filter(owner_id=options['owner_id'])
        
        if options['available_now']:
            today = datetime.now().date()
            accommodations = accommodations.filter(available_from__lte=today, available_until__gte=today)
        
        if options['min_price']:
            accommodations = accommodations.filter(daily_price__gte=options['min_price'])
        
        if options['max_price']:
            accommodations = accommodations.filter(daily_price__lte=options['max_price'])
        
        if options['min_rating']:
            accommodations = accommodations.filter(rating__gte=options['min_rating'])
        
        if options['min_beds']:
            accommodations = accommodations.filter(beds__gte=options['min_beds'])
        
        if options['address_contains']:
            accommodations = accommodations.filter(
                Q(address__icontains=options['address_contains']) | 
                Q(geo_address__icontains=options['address_contains'])
            )
        
        # Check if any accommodations were found
        count = accommodations.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('No accommodations found matching your criteria.'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Found {count} accommodation(s):'))
        self.stdout.write('-' * 80)
        
        # Display accommodations
        for acc in accommodations:
            if options['detailed']:
                # Detailed view - show all information
                self.stdout.write(f'ID: {acc.id}')
                self.stdout.write(f'Type: {acc.get_type_display()}')
                self.stdout.write(f'Address: {acc.address}')
                
                # Check if geocoding information exists
                if acc.geo_address:
                    self.stdout.write(f'Geo Address: {acc.geo_address}')
                else:
                    self.stdout.write('Geo Address: Not yet geocoded')
                    
                if acc.latitude is not None and acc.longitude is not None:
                    self.stdout.write(f'Coordinates: ({acc.latitude}, {acc.longitude})')
                else:
                    self.stdout.write('Coordinates: Not yet geocoded')
                    
                self.stdout.write(f'Available: {acc.available_from} to {acc.available_until}')
                self.stdout.write(f'Beds: {acc.beds}, Bedrooms: {acc.bedrooms}')
                self.stdout.write(f'Rating: {acc.rating}')
                self.stdout.write(f'Daily Price: ${acc.daily_price}')
                self.stdout.write(f'Owner: {acc.owner.name} (ID: {acc.owner.id})')
                self.stdout.write(f'Owner Contact: {acc.owner.contact_info}')
                self.stdout.write('-' * 80)
            else:
                # Summary view - show just the key information
                self.stdout.write(f'ID: {acc.id} | {acc.get_type_display()} | {acc.address} | ${acc.daily_price}/day | Rating: {acc.rating} | Owner: {acc.owner.name}')
        
        # Show command help
        self.stdout.write(self.style.SUCCESS('\nTip: Use --detailed flag to view more information'))
        self.stdout.write('Use --help to see all available filtering options') 