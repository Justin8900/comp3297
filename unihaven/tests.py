from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from django.utils.dateparse import parse_date
from django.core.management.base import CommandError
from unihaven.models import Accommodation, PropertyOwner
from decimal import Decimal
from datetime import datetime, timedelta

class AccommodationManagementTests(TestCase):
    def setUp(self):
        # Create a test property owner for some tests
        self.owner = PropertyOwner.objects.create(
            name="Test Owner",
            contact_info="test@example.com"
        )
        
        # Create test dates
        today = datetime.now().date()
        self.future_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')
        self.far_future_date = (today + timedelta(days=60)).strftime('%Y-%m-%d')

    def test_add_accommodation_with_existing_owner(self):
        """Test adding an accommodation using an existing property owner"""
        out = StringIO()
        args = [
            '--type', 'apartment',
            '--address', '123 Test Street',
            '--latitude', '22.3',
            '--longitude', '114.2',
            '--geo_address', 'Test District, Test City',
            '--available_from', self.future_date,
            '--available_until', self.far_future_date,
            '--beds', '2',
            '--bedrooms', '1',
            '--rating', '4.5',
            '--daily_price', '100.50',
            '--owner_id', str(self.owner.id)
        ]
        
        call_command('add_accommodation', *args, stdout=out)
        output = out.getvalue()
        
        # Check success message
        self.assertIn('Successfully added accommodation', output)
        
        # Verify database entry
        accommodation = Accommodation.objects.latest('id')
        self.assertEqual(accommodation.type, 'apartment')
        self.assertEqual(accommodation.address, '123 Test Street')
        self.assertEqual(accommodation.latitude, 22.3)
        self.assertEqual(accommodation.longitude, 114.2)
        self.assertEqual(accommodation.geo_address, 'Test District, Test City')
        self.assertEqual(accommodation.beds, 2)
        self.assertEqual(accommodation.bedrooms, 1)
        self.assertEqual(accommodation.rating, 4.5)
        self.assertEqual(accommodation.daily_price, Decimal('100.50'))
        self.assertEqual(accommodation.owner.id, self.owner.id)

    def test_add_accommodation_with_new_owner(self):
        """Test adding an accommodation while creating a new property owner"""
        out = StringIO()
        args = [
            '--type', 'house',
            '--address', '456 New Owner Road',
            '--latitude', '22.4',
            '--longitude', '114.3',
            '--geo_address', 'Another District, Test City',
            '--available_from', self.future_date,
            '--available_until', self.far_future_date,
            '--beds', '3',
            '--bedrooms', '2',
            '--rating', '4.8',
            '--daily_price', '150.75',
            '--owner_name', 'New Owner',
            '--owner_contact', 'new_owner@example.com'
        ]
        
        call_command('add_accommodation', *args, stdout=out)
        output = out.getvalue()
        
        # Check success messages
        self.assertIn('Created new property owner', output)
        self.assertIn('Successfully added accommodation', output)
        
        # Verify owner was created
        new_owner = PropertyOwner.objects.get(name='New Owner')
        self.assertEqual(new_owner.contact_info, 'new_owner@example.com')
        
        # Verify accommodation
        accommodation = Accommodation.objects.latest('id')
        self.assertEqual(accommodation.type, 'house')
        self.assertEqual(accommodation.owner.id, new_owner.id)

    def test_list_accommodations_with_filters(self):
        """Test listing accommodations with various filters"""
        # Create some test accommodations with different properties
        today = datetime.now().date()
        
        # First accommodation - available now, high price
        Accommodation.objects.create(
            type='apartment',
            address='111 Current Place',
            latitude=22.1,
            longitude=114.1,
            geo_address='Central District',
            available_from=today - timedelta(days=10),
            available_until=today + timedelta(days=20),
            beds=2,
            bedrooms=1,
            rating=4.0,
            daily_price=Decimal('200.00'),
            owner=self.owner
        )
        
        # Second accommodation - available later, low price
        Accommodation.objects.create(
            type='studio',
            address='222 Future Street',
            latitude=22.2,
            longitude=114.2,
            geo_address='Western District',
            available_from=today + timedelta(days=30),
            available_until=today + timedelta(days=60),
            beds=1,
            bedrooms=1,
            rating=3.5,
            daily_price=Decimal('80.00'),
            owner=self.owner
        )
        
        # Test filter by available now
        out = StringIO()
        call_command('list_accommodations', '--available_now', stdout=out)
        output = out.getvalue()
        self.assertIn('111 Current Place', output)
        self.assertNotIn('222 Future Street', output)
        
        # Test filter by price range
        out = StringIO()
        call_command('list_accommodations', '--min_price', '100', '--max_price', '250', stdout=out)
        output = out.getvalue()
        self.assertIn('111 Current Place', output)
        self.assertNotIn('222 Future Street', output)
        
        # Test filter by address
        out = StringIO()
        call_command('list_accommodations', '--address_contains', 'Western', stdout=out)
        output = out.getvalue()
        self.assertNotIn('111 Current Place', output)
        self.assertIn('222 Future Street', output)
        
        # Test with detailed output
        out = StringIO()
        call_command('list_accommodations', '--id', '1', '--detailed', stdout=out)
        output = out.getvalue()
        self.assertIn('Geo Address:', output)
        self.assertIn('Coordinates:', output)
        self.assertIn('Owner Contact:', output)
