from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from unihaven.utils.notifications import send_reservation_confirmation, send_reservation_update
import logging
from django.dispatch import receiver
from django.db.models.signals import post_save


# Create your models here.

class PropertyOwner(models.Model):
    """
    Model representing a property owner in the system.
    
    Attributes:
        user (User): The Django User associated with this property owner
        name (str): The name of the property owner
        phone_no (str): Phone number of the property owner
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=255)

    def __str__(self):
        """
        String representation of the PropertyOwner.
        
        Returns:
            str: The name of the property owner
        """
        return self.name

class CEDARSSpecialist(models.Model):
    """
    Model representing a CEDARS (Centre of Development and Resources for Students) specialist.
    
    Attributes:
        user (User): The Django User associated with this CEDARS specialist
        name (str): Name of the CEDARS specialist
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        """
        String representation of the CEDARSSpecialist.
        
        Returns:
            str: The name of the CEDARS specialist
        """
        return self.name
    
    def addAccommodation(self, accommodation_data):
        """
        Add a new accommodation to the system.
        
        Args:
            accommodation_data (dict): Data for creating the new accommodation
            
        Returns:
            Accommodation: The newly created accommodation
        """
        accommodation = Accommodation.objects.create(**accommodation_data)
        return accommodation
    
    def updateAccommodation(self, accommodation_id, updated_data):
        """
        Update an existing accommodation.
        
        Args:
            accommodation_id (int): ID of the accommodation to update
            updated_data (dict): New data for the accommodation
            
        Returns:
            Accommodation: The updated accommodation
        """
        accommodation = Accommodation.objects.get(id=accommodation_id)
        for key, value in updated_data.items():
            setattr(accommodation, key, value)
        accommodation.save()
        return accommodation
    
    def cancelReservation(self, reservation_id):
        """
        Cancel a reservation.
        
        Args:
            reservation_id (str): ID of the reservation to cancel
            
        Returns:
            Reservation: The cancelled reservation
        """
        reservation = Reservation.objects.get(id=reservation_id)
        old_status = reservation.status
        reservation.status = 'cancelled'
        reservation.cancelled_by = 'specialist'
        reservation.save()
        
        # Send update notification
        from unihaven.utils.notifications import send_reservation_update
        send_reservation_update(reservation, old_status)
        
        return reservation
    
    def viewReservations(self):
        """
        View all reservations in the system.
        
        Returns:
            QuerySet: All reservations
        """
        return Reservation.objects.all()
    
    def receiveNotifications(self):
        """
        Receive notifications about system events.
        
        Returns:
            list: List of notifications
        """
        # Implementation would depend on notification system
        return []

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
        daily_price (Decimal): Price per day
        owner (PropertyOwner): Foreign key to the property owner
        specialist (CEDARSSpecialist): Foreign key to the managing specialist
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
    daily_price = models.DecimalField(max_digits=10, decimal_places=2)
    owner = models.ForeignKey(PropertyOwner, on_delete=models.CASCADE, related_name="accommodations")
    specialist = models.ForeignKey(CEDARSSpecialist, on_delete=models.SET_NULL, null=True, related_name="managed_accommodations")

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
    
    @property
    def average_rating(self):
        """
        Calculate the average rating for this accommodation.
        
        Returns:
            float: Average rating score
        """
        ratings = Rating.objects.filter(reservation__accommodation=self)
        if not ratings.exists():
            return 0
        return sum(r.score for r in ratings) / ratings.count()

class HKUMember(models.Model):
    """
    Model representing a member of the Hong Kong University.
    
    Attributes:
        user (User): The Django User associated with this HKU member
        uid (str): Unique identifier for the HKU member (primary key)
        name (str): Name of the HKU member
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    uid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        """
        String representation of the HKUMember.
        
        Returns:
            str: The name of the HKU member
        """
        return self.name
    
    def searchAccommodation(self, **filters):
        """
        Search for accommodations based on given filters.
        
        Args:
            **filters: Filters to apply to the search
            
        Returns:
            QuerySet: Filtered accommodations
        """
        return Accommodation.objects.filter(**filters)
    
    def reserveAccommodation(self, accommodation_id, start_date, end_date):
        """
        Reserve an accommodation.
        
        Args:
            accommodation_id (int): ID of the accommodation to reserve
            start_date (Date): Start date of the reservation
            end_date (Date): End date of the reservation
            
        Returns:
            Reservation: The new reservation
        """
        accommodation = Accommodation.objects.get(id=accommodation_id)
        reservation = Reservation.objects.create(
            member=self,
            accommodation=accommodation,
            start_date=start_date,
            end_date=end_date,
            status='pending'
        )
        
        # Send confirmation notification
        from unihaven.utils.notifications import send_reservation_confirmation
        send_reservation_confirmation(reservation)
        
        return reservation
    
    def cancelReservation(self, reservation_id):
        """
        Cancel a reservation.
        
        Args:
            reservation_id (str): ID of the reservation to cancel
            
        Returns:
            Reservation: The cancelled reservation
        """
        reservation = Reservation.objects.get(id=reservation_id, member=self)
        old_status = reservation.status
        reservation.status = 'cancelled'
        reservation.cancelled_by = 'member'
        reservation.save()
        
        # Send update notification
        from unihaven.utils.notifications import send_reservation_update
        send_reservation_update(reservation, old_status)
        
        return reservation
    
    def rateAccommodation(self, reservation_id, score, comment=None):
        """
        Rate an accommodation based on a reservation.
        
        Args:
            reservation_id (str): ID of the reservation for the rating
            score (int): Rating score between 0 and 5
            comment (str, optional): Optional comment for the rating
            
        Returns:
            Rating: The new rating
        """
        reservation = Reservation.objects.get(id=reservation_id, member=self, status='completed')
        rating = Rating.objects.create(
            reservation=reservation,
            score=score,
            comment=comment
        )
        return rating
    
    def get_active_reservations_count(self):
        """
        Get the count of active reservations for this member.
        
        Active reservations are those with status 'pending' or 'confirmed'.
        
        Returns:
            int: Number of active reservations
        """
        return Reservation.objects.filter(
            member=self,
            status__in=['pending', 'confirmed']
        ).count()

class Reservation(models.Model):
    """
    Model representing a reservation for an accommodation.
    
    Attributes:
        id (str): Unique identifier for the reservation
        status (str): Status of the reservation
        start_date (Date): Start date of the reservation
        end_date (Date): End date of the reservation
        cancelled_by (str): Who cancelled the reservation (if applicable)
        member (HKUMember): Foreign key to the HKU member making the reservation
        accommodation (Accommodation): Foreign key to the accommodation being reserved
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    member = models.ForeignKey(HKUMember, on_delete=models.CASCADE, related_name='reservations')
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='reservations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateField()
    end_date = models.DateField()
    cancelled_by = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    
    def __str__(self):
        """
        String representation of the Reservation.
        
        Returns:
            str: Description of the reservation
        """
        return f"{self.member} - {self.accommodation} ({self.start_date} to {self.end_date})"
        
    def cancel(self, user_type='member'):
        """
        Cancel the reservation and send a notification.

        Args:
            user_type (str): The type of user cancelling the reservation (e.g., 'member' or 'specialist').

        Returns:
            Reservation: The updated reservation instance.
        """
        old_status = self.status
        self.status = 'cancelled'
        self.cancelled_by = user_type
        self.save()
        send_reservation_update(self, old_status)
        logger.info(f"Reservation #{self.id} has been cancelled by {user_type}.")
        return self
@receiver(post_save, sender=Reservation)
def handle_reservation_updates(sender, instance, created, **kwargs):
    """
    Signal to handle reservation-related notifications and logging.

    Args:
        sender: The model class that sent the signal.
        instance: The instance of the model that was saved.
        created: A boolean indicating if the instance is newly created.
        kwargs: Additional keyword arguments.
    """
    if created: 
        logger.info(f"New reservation created: {instance.member.name} reserved {instance.accommodation.address} from {instance.start_date} to {instance.end_date}.")

        success = send_reservation_confirmation(instance)
        if success:
            logger.info(f"Reservation confirmation email sent for reservation #{instance.id}")
        else:
            logger.error(f"Failed to send reservation confirmation email for reservation #{instance.id}")

    elif instance.status == 'cancelled':
        logger.info(f"Reservation #{instance.id} has been cancelled by {instance.cancelled_by}.")
        old_status = 'confirmed'
        
    
        success = send_reservation_update(instance, old_status)
        if success:
            logger.info(f"Reservation cancellation email sent for reservation #{instance.id}")
        else:
            logger.error(f"Failed to send reservation cancellation email for reservation #{instance.id}")


class Rating(models.Model):
    """
    Model representing a rating for an accommodation.
    
    Attributes:
        score (int): Rating score between 0 and 5
        date_rated (Date): Date when the rating was submitted
        comment (str): Optional comment for the rating
        reservation (Reservation): Foreign key to the reservation this rating is for
    """
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='rating')
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    date_rated = models.DateField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)
    
    def __str__(self):
        """
        String representation of the Rating.
        
        Returns:
            str: Description of the rating
        """
        return f"Rating {self.score}/5 for {self.reservation.accommodation}"
