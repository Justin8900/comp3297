from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.db.models import UniqueConstraint
import logging

# Create your models here.
class University(models.Model):
    """
    Model representing a university in the system.
    
    Attributes:
        code (char): the university code (e.g., HKU, CUHK, HKUST)
    """
    HKU = 'HKU'
    CUHK = 'CU'
    HKUST = 'HKUST'

    UNIVERSITY_CHOICES = [
        (HKU, 'University of Hong Kong'),
        (CUHK, 'Chinese University of Hong Kong'),
        (HKUST, 'Hong Kong University of Science and Technology'),
    ]
    code = models.CharField(max_length=10, choices=UNIVERSITY_CHOICES, unique=True)
    name = models.CharField(max_length=255, default='')

    def __str__(self):
        return self.name
    
class PropertyOwner(models.Model):
    """
    Model representing a property owner in the system.
    
    Attributes:
        user (User): The Django User associated with this property owner
        name (str): The name of the property owner
        phone_no (str): Phone number of the property owner
        email (str): Email address of the property owner (optional)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, blank=True, null=True) # Add optional email field

    def __str__(self):
        """
        String representation of the PropertyOwner.
        
        Returns:
            str: The name of the property owner
        """
        return self.name

class Specialist(models.Model):
    """
    Model representing a university specialist who manages accommodations and reservations.
    
    Attributes:
        user (User): The Django User associated with this specialist.
        name (str): Name of the specialist.
        university (University): The university this specialist belongs to.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="specialists")

    def __str__(self):
        return f"{self.name} ({self.university.code} Specialist)"

class Accommodation(models.Model):
    """
    Model representing an accommodation listing in the system.
    
    Attributes:
        type (str): Type of accommodation.
        address (str): Basic address line.
        building_name (str): Building name.
        room_number (str): Room number, optional.
        flat_number (str): Flat number.
        floor_number (str): Floor number.
        latitude (float): Latitude coordinate (optional).
        longitude (float): Longitude coordinate (optional).
        geo_address (str): Geocoded address string (required for uniqueness).
        available_from (date): Start date of availability.
        available_until (date): End date of availability.
        beds (int): Number of beds available.
        bedrooms (int): Number of bedrooms.
        daily_price (Decimal): Price per day.
        owner (PropertyOwner): Foreign key to the property owner.
        available_at_universities (ManyToManyField): Universities offering this accommodation.
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
    building_name = models.CharField(max_length=255, default='', blank=True)
    room_number = models.CharField(max_length=50, null=True, blank=True)
    flat_number = models.CharField(max_length=50, default='')
    floor_number = models.CharField(max_length=50, default='')
    geo_address = models.CharField(max_length=255, default='')

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    available_from = models.DateField()
    available_until = models.DateField()
    beds = models.IntegerField()
    bedrooms = models.IntegerField()
    daily_price = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name="accommodations")
    available_at_universities = models.ManyToManyField(University, related_name="available_accommodations")

    class Meta:
        constraints = [
            UniqueConstraint(fields=['room_number', 'flat_number', 'floor_number', 'geo_address'], name='unique_physical_address')
        ]

    def __str__(self):
        """
        String representation of the Accommodation. Returns the unique address components.
        """
        addr_parts = [self.floor_number, self.flat_number]
        if self.room_number:
            addr_parts.insert(0, self.room_number)
        return f"{', '.join(addr_parts)} - {self.building_name}"

    def update_geocoding(self):
        """
        Updates the geocoding information (latitude, longitude, geo_address) for this accommodation
        by calling the geocoding API. Prioritizes building_name, then falls back to address.

        Returns:
            bool: True if geocoding was successful, False otherwise
        """
        from unihaven.utils.geocoding import geocode_address

        address_to_geocode = None
        source_field = None

        # Prioritize building_name
        if self.building_name and self.building_name.strip():
            address_to_geocode = self.building_name.strip()
            source_field = 'building_name'
        # Fallback to address field
        elif self.address and self.address.strip():
            address_to_geocode = self.address.strip()
            source_field = 'address'

        # If neither field provides usable input, skip geocoding
        if not address_to_geocode:
            logger.warning(f"Skipping geocoding for Acc ID {self.id}: Both building_name and address are empty.")
            return False

        logger.debug(f"Geocoding Acc ID {self.id} using field '{source_field}': '{address_to_geocode}'")

        lat, lng, geo = geocode_address(address_to_geocode)

        if lat is not None and lng is not None and geo is not None:
            self.latitude = lat
            self.longitude = lng
            self.geo_address = geo
            self.save(update_fields=['latitude', 'longitude', 'geo_address'])
            logger.info(f"Successfully geocoded Acc ID {self.id} using {source_field}.")
            return True
        else:
            logger.warning(f"Geocoding failed for Acc ID {self.id} using {source_field}: '{address_to_geocode}'")
            return False
    
    @property
    def average_rating(self):
        """
        Calculate the average rating for this accommodation.
        Considers ratings from all universities unless filtered elsewhere.
        """
        ratings = self.ratings.all()
        if not ratings.exists():
            return 0.0
        return sum(r.score for r in ratings) / ratings.count()

    @property
    def rating_count(self):
        """
        Get the total number of ratings for this accommodation.
        """
        return self.ratings.count()

# --- Concrete Member Model --- 
class Member(models.Model):
    """Concrete model representing a university member."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) # Add user link
    # Assuming UID is unique across ALL universities and can serve as PK
    uid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="members") # related_name is OK here
    # Replace generic contact with specific fields
    phone_number = models.CharField(max_length=20, blank=True, null=True) # Adjust max_length as needed
    email = models.EmailField(max_length=254, blank=True, null=True) # Standard max length for emails

    def __str__(self):
        return f"{self.name} ({self.uid} - {self.university.code})"

logger = logging.getLogger('django')
class Reservation(models.Model):
    """
    Model representing a reservation for an accommodation.
    
    Attributes:
        status (str): Status of the reservation.
        start_date (Date): Start date of the reservation.
        end_date (Date): End date of the reservation.
        cancelled_by (str): Who cancelled the reservation (if applicable).
        member (Member): Foreign key to the member making the reservation.
        accommodation (Accommodation): Foreign key to the accommodation being reserved.
        university (University): Foreign key to the university context of this reservation (derived from member).
        created_at (DateTime): Timestamp of creation.
        updated_at (DateTime): Timestamp of last update.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='reservations')
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='reservations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateField()
    end_date = models.DateField()
    cancelled_by = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="reservations", null=True)

    def __str__(self):
        """
        String representation of the Reservation.
        """
        return f"{self.member} - {self.accommodation} ({self.start_date} to {self.end_date}) [{self.status}]"
        
    def save(self, *args, **kwargs):
        """
        Override save to ensure the university is set from the member if not already set.
        """
        if not self.university_id and self.member_id:
             # Fetch member to get university - slightly less efficient but necessary
             try: 
                 member_instance = Member.objects.get(pk=self.member_id)
                 self.university = member_instance.university
             except Member.DoesNotExist:
                 logger.error(f"Attempted to save Reservation with invalid member_id: {self.member_id}")
                 pass 
        super().save(*args, **kwargs)

class Rating(models.Model):
    """
    Model representing a rating for an accommodation, linked via a Reservation.
    
    Attributes:
        reservation (Reservation): The completed reservation this rating is for.
        score (int): Rating score (0-5).
        date_rated (Date): Date rating was submitted.
        comment (str): Optional comment.
    """
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='rating')
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    date_rated = models.DateField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)
    
    def __str__(self):
        """
        String representation of the Rating.
        """
        return f"Rating {self.score}/5 for {self.reservation.accommodation} (Res ID: {self.reservation.id})"


class UniversityLocation(models.Model):
    """Model representing specific named locations (campuses, buildings) for a university."""
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=255, help_text="e.g., Main Campus, Sassoon Road Campus")
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        # Ensure location names are unique within each university
        unique_together = ['university', 'name']
        ordering = ['university__code', 'name']

    def __str__(self):
        return f"{self.name} ({self.university.code})"
