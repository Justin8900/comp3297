from rest_framework import serializers
from decimal import Decimal
from .models import (
    University, PropertyOwner, Accommodation, Member, Specialist,
    Reservation, Rating
)
import logging

logger = logging.getLogger(__name__)

# --- Basic Serializers ---

class UniversitySerializer(serializers.ModelSerializer):
    """Serializer for University details."""
    class Meta:
        model = University
        # Include name for better representation
        fields = ['code', 'name']
        read_only_fields = ['code', 'name'] # Usually universities aren't created/modified via API

class PropertyOwnerSerializer(serializers.ModelSerializer):
    """Serializer for the PropertyOwner model."""
    class Meta:
        model = PropertyOwner
        fields = ['id', 'name', 'phone_no']
        # Consider if owner endpoint allows creation/update or is managed elsewhere

# --- Generalized Member & Specialist Serializers ---

class MemberSerializer(serializers.ModelSerializer):
    """Serializer for the concrete Member model."""
    university = serializers.SlugRelatedField(slug_field='code', read_only=True)
    
    class Meta:
        model = Member # Point to the concrete Member model
        fields = ['uid', 'name', 'university']
        # Allow UID to be provided during creation
        read_only_fields = ['university'] # University is set by perform_create

class SpecialistSerializer(serializers.ModelSerializer):
    """Serializer for the unified Specialist model."""
    university = serializers.SlugRelatedField(slug_field='code', read_only=True)

    class Meta:
        model = Specialist
        fields = ['id', 'name', 'university']
        # Modifications typically restricted to admin interface or specific logic
        read_only_fields = ['id', 'university']


# --- Accommodation Serializer ---

class AccommodationSerializer(serializers.ModelSerializer):
    """Serializer for the Accommodation model.
    Handles M2M relationship with University and new address fields.
    Owner association via owner_id."""
    owner = PropertyOwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=PropertyOwner.objects.all(),
        write_only=True,
        source='owner',
        required=True, # Assuming owner is always required
        label="Existing Property Owner ID" # Corrected quotes
    )

    # Handle M2M relationship with University
    available_at_universities = serializers.SlugRelatedField(
         queryset=University.objects.all(),
         slug_field='code',
         many=True,
         label="Universities offering this accommodation (use codes like 'HKU', 'CU')" # Corrected quotes
    )

    # Add new address fields
    geo_address = serializers.CharField(read_only=True, required=False)
    latitude = serializers.FloatField(read_only=True, required=False)
    longitude = serializers.FloatField(read_only=True, required=False)

    # Add average rating (read-only property from model)
    average_rating = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)

    # Validation for numeric fields
    beds = serializers.IntegerField(min_value=0, label="Number of beds (must be 0 or greater)") # Corrected quotes
    bedrooms = serializers.IntegerField(min_value=0, label="Number of bedrooms (must be 0 or greater)") # Corrected quotes
    daily_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label="Daily price (positive amount)" # Corrected quotes
    )

    class Meta:
        model = Accommodation
        fields = [
            'id', 'type',
            # Address components
            'address',
            'room_number', 'flat_number', 'floor_number',
            # Geocoding related
            'latitude', 'longitude', 'geo_address',
            # Availability & Specs
            'available_from', 'available_until', 'beds', 'bedrooms',
            'daily_price',
            # Relationships
            'owner', 'owner_id',
            'available_at_universities',
            # Read-only computed fields
            'average_rating', 'rating_count'
        ]
        read_only_fields = ['id', 'latitude', 'longitude', 'geo_address', 'average_rating', 'rating_count']

    def validate_available_at_universities(self, value):
        """Ensure at least one university is selected."""
        if not value:
            raise serializers.ValidationError("At least one university must be selected.")
        return value

    def validate(self, data):
        """Validate dates: available_until must be after available_from."""
        # logger.info(f"[Serializer Validate] Input data: {data}") # Log input data
        start = data.get('available_from', getattr(self.instance, 'available_from', None))
        end = data.get('available_until', getattr(self.instance, 'available_until', None))

        if start and end and end < start:
            raise serializers.ValidationError({"available_until": "End date must be after start date."})

        # Log validated data BEFORE returning from serializer validate
        # logger.info(f"[Serializer Validate] Returning validated data: {data}") 
        return data


# --- Rating Serializer ---

class RatingSerializer(serializers.ModelSerializer):
    """Serializer for the Rating model.
    Handles creation and display of ratings, linked to a reservation."""
    # Display related info read-only
    member_uid = serializers.CharField(source='reservation.member.uid', read_only=True)
    accommodation_id = serializers.IntegerField(source='reservation.accommodation.id', read_only=True)
    accommodation_details = serializers.CharField(source='reservation.accommodation.__str__', read_only=True) # Use __str__

    # Use PrimaryKeyRelatedField for writing the reservation link
    reservation = serializers.PrimaryKeyRelatedField(
        queryset=Reservation.objects.all(), # Queryset for validation
        write_only=True, # Only used for creating/linking the rating
        label="Reservation ID being rated" # Corrected quotes
    )

    class Meta:
        model = Rating
        fields = [
            'id',
            'reservation', # Write-only field for linking
            'score', 'comment', 'date_rated',
            # Read-only fields for context
            'member_uid', 'accommodation_id', 'accommodation_details'
            ]
        read_only_fields = ['id', 'date_rated', 'member_uid', 'accommodation_id', 'accommodation_details']


# --- Reservation Serializer ---

class ReservationSerializer(serializers.ModelSerializer):
    """Serializer for the Reservation model.
    Handles creation by members (self) or specialists (for a member).
    Handles display of reservations."""
    # Read-only nested serializers for display
    member = MemberSerializer(read_only=True)
    # Use a simple representation for accommodation to avoid overly nested data
    accommodation_details = serializers.CharField(source='accommodation.__str__', read_only=True) # Use __str__
    university = serializers.SlugRelatedField(slug_field='code', read_only=True)
    rating = RatingSerializer(read_only=True) # Display nested rating if it exists

    # Write-only fields for creation
    accommodation = serializers.PrimaryKeyRelatedField(
        queryset=Accommodation.objects.all(), 
        write_only=True
    )
    member_uid = serializers.CharField(
         write_only=True, 
         required=False, 
         label="Member UID (Required if Specialist is creating reservation)" # Corrected quotes
    )

    class Meta:
        model = Reservation
        fields = [
            'id', 'status', 'start_date', 'end_date', 'cancelled_by', 
            'university', 'member', 'accommodation_details', 'rating', 
            'accommodation', 'member_uid' 
        ]
        # Make status read-only here; updates handled in view
        read_only_fields = ['id', 'status', 'cancelled_by', 'university', 'member', 'accommodation_details', 'rating']
        # Note: status might be updatable by specialists via PUT/PATCH actions in the view

    def validate(self, data):
        """Validate dates and check for overlaps."""
        # Get instance if performing an update
        instance = getattr(self, 'instance', None)

        start_date = data.get('start_date', getattr(instance, 'start_date', None))
        end_date = data.get('end_date', getattr(instance, 'end_date', None))
        accommodation = data.get('accommodation', getattr(instance, 'accommodation', None))

        # 1. Validate Date Order
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})

        # 2. Check for Overlapping Reservations for the *specific* accommodation
        if start_date and end_date and accommodation:
            overlapping_reservations = Reservation.objects.filter(
                accommodation=accommodation,
                status__in=['pending', 'confirmed'],
                start_date__lt=end_date, # Starts before the new one ends
                end_date__gt=start_date # Ends after the new one starts
            )
            # If updating, exclude the current reservation itself from the check
            if instance:
                overlapping_reservations = overlapping_reservations.exclude(pk=instance.pk)

            if overlapping_reservations.exists():
                raise serializers.ValidationError(
                    "Accommodation is not available for the selected dates due to an existing reservation."
                )

        # Member UID validation is handled in the view's perform_create
        
        return data

# --- Utility Serializers ---

class AccommodationSearchSerializer(serializers.Serializer):
    """Serializer for accommodation search parameters.
    Needs review/update if search endpoint is reimplemented with new models/filters."""
    type = serializers.CharField(required=False, help_text="Filter by accommodation type")
    min_beds = serializers.IntegerField(required=False, help_text="Filter by minimum number of beds")
    # ... (add/update other fields as needed)
    max_price = serializers.FloatField(required=False, help_text="Filter by maximum price")
    available_from = serializers.DateField(required=False, help_text="Filter by availability start date (YYYY-MM-DD)")
    available_until = serializers.DateField(required=False, help_text="Filter by availability end date (YYYY-MM-DD)")
    # distance_from might need adjustment based on geocoding implementation
    # university_code = serializers.CharField(required=False) # Add filter by university? (Handled by view queryset now)