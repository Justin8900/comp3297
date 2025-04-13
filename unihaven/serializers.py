from rest_framework import serializers
from decimal import Decimal
from .models import PropertyOwner, Accommodation, HKUMember, CEDARSSpecialist, Reservation, Rating

class PropertyOwnerSerializer(serializers.ModelSerializer):
    """
    Serializer for the PropertyOwner model.
    
    Handles serialization and deserialization of PropertyOwner objects.
    
    Fields:
        id (int): Unique identifier
        name (str): Name of the property owner
        phone_no (str): Phone number of the property owner
    """
    class Meta:
        model = PropertyOwner
        fields = ['id', 'name', 'phone_no']

class HKUMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for the HKUMember model.
    
    Handles serialization and deserialization of HKU member objects.
    
    Fields:
        uid (str): Unique identifier (primary key)
        name (str): Name of the HKU member
    """
    class Meta:
        model = HKUMember
        fields = ['uid', 'name']

class CEDARSSpecialistSerializer(serializers.ModelSerializer):
    """
    Serializer for the CEDARSSpecialist model.
    
    Handles serialization and deserialization of CEDARS specialist objects.
    
    Fields:
        id (int): Unique identifier
        name (str): Name of the CEDARS specialist
    """
    class Meta:
        model = CEDARSSpecialist
        fields = ['id', 'name']

# Forward declaration for nested serializers
class ReservationSerializer(serializers.ModelSerializer):
    pass

class RatingSerializer(serializers.ModelSerializer):
    """
    Serializer for the Rating model.
    
    Handles serialization and deserialization of Rating objects.
    
    Fields:
        id (int): Unique identifier
        score (int): Rating score (0-5)
        date_rated (date): Date when the rating was submitted
        comment (str): Optional comment for the rating
        reservation (int): ID of the associated reservation
    """
    class Meta:
        model = Rating
        fields = ['id', 'score', 'date_rated', 'comment', 'reservation']
        read_only_fields = ['date_rated']

class AccommodationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Accommodation model.
    
    Provides comprehensive serialization for accommodation listings with support for:
    - Creating/updating accommodations
    - Handling property owner relationships
    - Validating dates and numeric fields
    - Automatic geocoding of addresses
    
    Fields:
        id (int): Unique identifier (read-only)
        type (str): Type of accommodation
        address (str): Physical address
        latitude (float): Latitude coordinate (read-only, auto-populated)
        longitude (float): Longitude coordinate (read-only, auto-populated)
        geo_address (str): Geocoded address (read-only, auto-populated)
        available_from (date): Start date of availability
        available_until (date): End date of availability
        beds (int): Number of beds (min: 0)
        bedrooms (int): Number of bedrooms (min: 0)
        daily_price (Decimal): Price per day (min: 0.01)
        owner (PropertyOwnerSerializer): Nested serializer for owner details
        owner_id (int): ID for selecting existing owner (write-only)
        specialist (CEDARSSpecialistSerializer): Nested serializer for specialist details
        specialist_id (int): ID for selecting existing specialist (write-only)
        average_rating (float): Average rating based on associated ratings
    """
    owner = PropertyOwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=PropertyOwner.objects.all(),
        write_only=True,
        source='owner',
        required=False,
        allow_null=True,
        label="Select existing owner (leave blank for new owner)"
    )
    
    specialist = CEDARSSpecialistSerializer(read_only=True)
    specialist_id = serializers.PrimaryKeyRelatedField(
        queryset=CEDARSSpecialist.objects.all(),
        write_only=True,
        source='specialist',
        required=False,
        allow_null=True,
        label="Select managing specialist"
    )
    
    # Fields for creating a new owner if owner_id is not provided
    owner_name = serializers.CharField(
        write_only=True, 
        required=False,
        label="New owner name (only if creating new owner)"
    )
    owner_phone = serializers.CharField(
        write_only=True, 
        required=False,
        label="New owner phone number (only if creating new owner)"
    )
    
    # Add validation for numeric fields
    beds = serializers.IntegerField(min_value=0, label="Number of beds (must be 0 or greater)")
    bedrooms = serializers.IntegerField(min_value=0, label="Number of bedrooms (must be 0 or greater)")
    average_rating = serializers.FloatField(read_only=True)
    daily_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label="Daily price (positive amount)"
    )
    
    # Make geocoding fields read-only since they'll be auto-populated
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    geo_address = serializers.CharField(read_only=True)
    
    class Meta:
        model = Accommodation
        fields = [
            'id', 'type', 'address', 'latitude', 'longitude', 'geo_address',
            'available_from', 'available_until', 'beds', 'bedrooms', 'average_rating',
            'daily_price', 'owner', 'owner_id', 'owner_name', 'owner_phone',
            'specialist', 'specialist_id'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        """
        Validate the accommodation data.
        
        Performs the following validations:
        1. Checks that available_until date is after available_from date
        2. Ensures either owner_id or both owner_name and owner_phone are provided
        3. Creates a new owner if owner_name and owner_phone are provided without owner_id
        
        Args:
            data (dict): The data to validate
            
        Returns:
            dict: The validated data
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate that available_until is after available_from
        if 'available_from' in data and 'available_until' in data:
            if data['available_until'] <= data['available_from']:
                raise serializers.ValidationError("Available until date must be after available from date")
        
        # Check that either owner_id or both owner_name and owner_phone are provided for creation
        if self.instance is None:  # Only for creation
            owner = data.get('owner')
            owner_name = data.pop('owner_name', None) if 'owner_name' in data else None
            owner_phone = data.pop('owner_phone', None) if 'owner_phone' in data else None
            
            if not owner and not (owner_name and owner_phone):
                raise serializers.ValidationError("Either owner_id or both owner_name and owner_phone must be provided")
            
            # If owner_name and owner_phone are provided but no owner_id, create a new owner
            if not owner and owner_name and owner_phone:
                new_owner = PropertyOwner.objects.create(
                    name=owner_name,
                    phone_no=owner_phone
                )
                data['owner'] = new_owner
        
        return data

# Complete the ReservationSerializer definition
class ReservationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Reservation model.
    
    Handles serialization and deserialization of Reservation objects.
    
    Fields:
        id (int): Unique identifier
        status (str): Status of the reservation
        start_date (date): Start date of the reservation
        end_date (date): End date of the reservation
        cancelled_by (str): Who cancelled the reservation (if applicable)
        member (HKUMemberSerializer): The HKU member making the reservation
        accommodation (AccommodationSerializer): The accommodation being reserved
        rating (RatingSerializer): Associated rating (if any)
    """
    member = HKUMemberSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=HKUMember.objects.all(),
        write_only=True,
        source='member'
    )
    accommodation = serializers.PrimaryKeyRelatedField(queryset=Accommodation.objects.all())
    rating = RatingSerializer(read_only=True)
    
    class Meta:
        model = Reservation
        fields = ['id', 'status', 'start_date', 'end_date', 'cancelled_by', 
                 'member', 'member_id', 'accommodation', 'rating']
        read_only_fields = ['id', 'cancelled_by']
    
    def validate(self, data):
        """
        Validate the reservation data.
        
        Performs the following validations:
        1. Checks that end_date is after start_date
        2. Checks if accommodation is available for the selected dates
        
        Args:
            data (dict): The data to validate
            
        Returns:
            dict: The validated data
            
        Raises:
            ValidationError: If validation fails
        """
        if 'start_date' in data and 'end_date' in data:
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError("End date must be after start date")
            
            # Check if accommodation is available for these dates
            accommodation = data['accommodation']
            if data['start_date'] < accommodation.available_from or data['end_date'] > accommodation.available_until:
                raise serializers.ValidationError("Accommodation is not available for the selected dates")
            
            # Check for conflicting reservations
            conflicting = Reservation.objects.filter(
                accommodation=accommodation,
                status__in=['pending', 'confirmed'],
                start_date__lt=data['end_date'],
                end_date__gt=data['start_date']
            )
            
            # Exclude current reservation when updating
            if self.instance:
                conflicting = conflicting.exclude(id=self.instance.id)
                
            if conflicting.exists():
                raise serializers.ValidationError("This accommodation is already reserved for the selected dates")
            
        return data 

class ReserveAccommodationSerializer(serializers.Serializer):
    """
    Serializer for reserving an accommodation.
    
    Fields:
        accommodation_id (int): ID of the accommodation to reserve
        start_date (date): Start date of the reservation (YYYY-MM-DD)
        end_date (date): End date of the reservation (YYYY-MM-DD)
        member_name (str): Name of the HKU member (only required for first-time users)
    """
    accommodation_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    member_name = serializers.CharField(required=False)

class CancelReservationSerializer(serializers.Serializer):
    """
    Serializer for cancelling a reservation.
    
    Fields:
        reservation_id (int): ID of the reservation to cancel
    """
    reservation_id = serializers.IntegerField()

class RateAccommodationSerializer(serializers.Serializer):
    """
    Serializer for rating an accommodation.
    
    Fields:
        reservation_id (int): ID of the completed reservation
        score (int): Rating score, 0-5
        comment (str): Optional comment about the stay
    """
    reservation_id = serializers.IntegerField()
    score = serializers.IntegerField(min_value=0, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)

class UpdateAccommodationSerializer(serializers.Serializer):
    """
    Serializer for updating an accommodation by a CEDARS specialist.
    
    Fields:
        accommodation_id (int): ID of the accommodation to update
        type (str): Type of accommodation (optional)
        address (str): Physical address (optional)
        available_from (date): Start date of availability (optional)
        available_until (date): End date of availability (optional)
        beds (int): Number of beds (optional)
        bedrooms (int): Number of bedrooms (optional)
        daily_price (decimal): Price per day (optional)
    """
    accommodation_id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=["apartment", "house", "villa", "studio", "hostel"], required=False)
    address = serializers.CharField(required=False)
    available_from = serializers.DateField(required=False)
    available_until = serializers.DateField(required=False)
    beds = serializers.IntegerField(min_value=0, required=False)
    bedrooms = serializers.IntegerField(min_value=0, required=False)
    daily_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01, required=False)

class ConfirmReservationSerializer(serializers.Serializer):
    """
    Serializer for confirming a reservation.
    This is a simple serializer as confirming only requires the reservation ID 
    which is already part of the URL.
    """
    pass 