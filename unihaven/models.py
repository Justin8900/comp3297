from django.db import models

# Create your models here.

class PropertyOwner(models.Model):
    name = models.CharField(max_length=255)
    contact_info = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Accommodation(models.Model):
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
    rating = models.FloatField()
    daily_price = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name="accommodations")

    def __str__(self):
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
    uid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class CEDARSSpecialist(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
