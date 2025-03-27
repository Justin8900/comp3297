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
    latitude = models.FloatField()
    longitude = models.FloatField()
    geo_address = models.CharField(max_length=255)
    available_from = models.DateField()  
    available_until = models.DateField()
    beds = models.IntegerField()
    bedrooms = models.IntegerField()
    rating = models.FloatField()
    daily_price = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name="accommodations")

    def __str__(self):
        return self.address

class HKUMember(models.Model):
    uid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class CEDARSSpecialist(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
