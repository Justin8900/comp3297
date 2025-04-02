from django.db import models

# Create your models here.

class PropertyOwner(models.Model):
    """
    Model representing a property owner in the system.
    
    Attributes:
        name (str): The name of the property owner
        contact_info (str): Contact information for the property owner
    """
    name = models.CharField(max_length=255)
    contact_info = models.CharField(max_length=255)

    def __str__(self):
        """
        String representation of the PropertyOwner.
        
        Returns:
            str: The name of the property owner
        """
        return self.name

class Accommodation(models.Model):
    """
    Model representing an accommodation listing in the system.
    
    Attributes:
        type (str): Type of accommodation (apartment, house, villa, studio, hostel)
        address (str): Physical address of the accommodation
        latitude (float): Latitude coordinate of the accommodation (optional)
        longitude (float): Longitude coordinate of the accommodation (optional)
        geo_address (str): Geocoded address string (optional)
        available_from (date): Start date of availability
        available_until (date): End date of availability
        beds (int): Number of beds available
        bedrooms (int): Number of bedrooms
        rating (int): Rating of the accommodation
        daily_price (Decimal): Price per day
        owner (PropertyOwner): Foreign key to the property owner
    """
    TYPE_CHOICES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('hostel', 'Hostel'),
    ]
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    address = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    geo_address = models.CharField(max_length=255, null=True, blank=True)
    available_from = models.DateField()  
    available_until = models.DateField()
    beds = models.IntegerField()
    bedrooms = models.IntegerField()
    rating = models.IntegerField()
    daily_price = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name="accommodations")

    def __str__(self):
        """
        String representation of the Accommodation.
        
        Returns:
            str: The address of the accommodation
        """
        return self.address

    def update_geocoding(self):
        """
        Updates the geocoding information (latitude, longitude, geo_address) for this accommodation
        by calling the geocoding API with the current address.
        
        Returns:
            bool: True if geocoding was successful, False otherwise
        """
        from unihaven.utils.geocoding import geocode_address
        
        lat, lng, geo = geocode_address(self.address)
        
        if lat is not None and lng is not None and geo is not None:
            self.latitude = lat
            self.longitude = lng
            self.geo_address = geo
            self.save()
            return True
        return False

class HKUMember(models.Model):
    """
    Model representing a member of the Hong Kong University.
    
    Attributes:
        uid (str): Unique identifier for the HKU member (primary key)
        name (str): Name of the HKU member
    """
    uid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        """
        String representation of the HKUMember.
        
        Returns:
            str: The name of the HKU member
        """
        return self.name

class CEDARSSpecialist(models.Model):
    """
    Model representing a CEDARS (Centre of Development and Resources for Students) specialist.
    
    Attributes:
        name (str): Name of the CEDARS specialist
    """
    name = models.CharField(max_length=255)

    def __str__(self):
        """
        String representation of the CEDARSSpecialist.
        
        Returns:
            str: The name of the CEDARS specialist
        """
        return self.name
