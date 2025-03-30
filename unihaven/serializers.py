from rest_framework import serializers
from decimal import Decimal
from .models import PropertyOwner, Accommodation, HKUMember, CEDARSSpecialist

class PropertyOwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyOwner
        fields = ['id', 'name', 'contact_info']

class AccommodationSerializer(serializers.ModelSerializer):
    owner = PropertyOwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=PropertyOwner.objects.all(),
        write_only=True,
        source='owner',
        required=False,
        allow_null=True,
        label="Select existing owner (leave blank for new owner)"
    )
    
    # Fields for creating a new owner if owner_id is not provided
    owner_name = serializers.CharField(
        write_only=True, 
        required=False,
        label="New owner name (only if creating new owner)"
    )
    owner_contact = serializers.CharField(
        write_only=True, 
        required=False,
        label="New owner contact info (only if creating new owner)"
    )
    
    # Add validation for numeric fields
    beds = serializers.IntegerField(min_value=0, label="Number of beds (must be 0 or greater)")
    bedrooms = serializers.IntegerField(min_value=0, label="Number of bedrooms (must be 0 or greater)")
    rating = serializers.IntegerField(min_value=0, max_value=5, label="Rating (between 0 and 5)")
    daily_price = serializers.IntegerField(
        min_value=1,
        label="Daily price in whole numbers (positive integer)"
    )
    
    # Make geocoding fields read-only since they'll be auto-populated
    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    geo_address = serializers.CharField(read_only=True)
    
    class Meta:
        model = Accommodation
        fields = [
            'id', 'type', 'address', 'latitude', 'longitude', 'geo_address',
            'available_from', 'available_until', 'beds', 'bedrooms', 'rating',
            'daily_price', 'owner', 'owner_id', 'owner_name', 'owner_contact'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        # Validate that available_until is after available_from
        if 'available_from' in data and 'available_until' in data:
            if data['available_until'] <= data['available_from']:
                raise serializers.ValidationError("Available until date must be after available from date")
        
        # Check that either owner_id or both owner_name and owner_contact are provided for creation
        if self.instance is None:  # Only for creation
            owner = data.get('owner')
            owner_name = data.pop('owner_name', None) if 'owner_name' in data else None
            owner_contact = data.pop('owner_contact', None) if 'owner_contact' in data else None
            
            if not owner and not (owner_name and owner_contact):
                raise serializers.ValidationError("Either owner_id or both owner_name and owner_contact must be provided")
            
            # If owner_name and owner_contact are provided but no owner_id, create a new owner
            if not owner and owner_name and owner_contact:
                new_owner = PropertyOwner.objects.create(
                    name=owner_name,
                    contact_info=owner_contact
                )
                data['owner'] = new_owner
        
        return data

class HKUMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = HKUMember
        fields = ['uid', 'name']

class CEDARSSpecialistSerializer(serializers.ModelSerializer):
    class Meta:
        model = CEDARSSpecialist
        fields = ['id', 'name'] 