from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q, Avg
from rest_framework import viewsets, status, filters, permissions
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from datetime import datetime
from decimal import Decimal
from .models import *
from .serializers import (
    PropertyOwnerSerializer, AccommodationSerializer, HKUMemberSerializer,
    CEDARSSpecialistSerializer, ReservationSerializer, RatingSerializer,
    ReserveAccommodationSerializer, CancelReservationSerializer, RateAccommodationSerializer,
    ConfirmReservationSerializer
)
from .permissions import *
from .utils.geocoding import geocode_address
import math
# Create your views here.

# API Views
class PropertyOwnerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing property owners.
    Provides CRUD operations for PropertyOwner model.
    """
    queryset = PropertyOwner.objects.all()
    serializer_class = PropertyOwnerSerializer
    
    def get_permissions(self):
        """
        Since authentication is handled by the CEDARS frontend, 
        we're using AllowAny permission and filtering based on role header/parameter.
        """
        return [permissions.AllowAny()]
        
    def create(self, request, *args, **kwargs):
        """
        Create a new property owner.
        Only CEDARS specialists can create property owners.
        """
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can create property owners"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
        
    def update(self, request, *args, **kwargs):
        """
        Update a property owner.
        Only CEDARS specialists can update property owners.
        """
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can update property owners"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
        
    def destroy(self, request, *args, **kwargs):
        """
        Delete a property owner.
        Only CEDARS specialists can delete property owners.
        """
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can delete property owners"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

class AccommodationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing accommodations.
    Provides CRUD operations and search functionality for Accommodation model.
    
    Features:
    - Filtering by type, price, rating, beds, bedrooms, availability
    - Geocoding of addresses
    - Distance-based search from HKU locations
    - Custom search endpoint
    """
    queryset = Accommodation.objects.all().select_related('owner', 'specialist')
    serializer_class = AccommodationSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['daily_price', 'beds', 'bedrooms', 'available_from', 'available_until']
    
    def get_permissions(self):
        """
        Since authentication is handled by the CEDARS frontend, 
        we're using AllowAny permission and filtering based on role header/parameter.
        """
        return [permissions.AllowAny()]
        
    def create(self, request, *args, **kwargs):
        """
        Create a new accommodation.
        Only CEDARS specialists can create accommodations.
        """
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can create accommodations"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
        
    def update(self, request, *args, **kwargs):
        """
        Update an accommodation.
        Only CEDARS specialists can update accommodations.
        """
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can update accommodations"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
        
    def destroy(self, request, *args, **kwargs):
        """
        Delete an accommodation.
        Only CEDARS specialists can delete accommodations.
        """
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can delete accommodations"},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    def get_queryset(self):
        """
        Get filtered queryset based on query parameters.
        
        Available filters:
        - type: Filter by accommodation type
        - owner_id: Filter by property owner
        - specialist_id: Filter by CEDARS specialist
        - available_now: Filter currently available accommodations
        - min_price/max_price: Filter by price range
        - min_rating: Filter by minimum average rating
        - min_beds: Filter by minimum number of beds
        - address_contains: Filter by address text
        
        Returns:
            QuerySet: Filtered queryset of accommodations
        """
        queryset = super().get_queryset()
        
        # Apply filters based on query parameters
        if 'type' in self.request.query_params:
            queryset = queryset.filter(type=self.request.query_params['type'])
        
        if 'owner_id' in self.request.query_params:
            queryset = queryset.filter(owner_id=self.request.query_params['owner_id'])
            
        if 'specialist_id' in self.request.query_params:
            queryset = queryset.filter(specialist_id=self.request.query_params['specialist_id'])
        
        if 'available_now' in self.request.query_params and self.request.query_params['available_now'].lower() == 'true':
            today = datetime.now().date()
            queryset = queryset.filter(available_from__lte=today, available_until__gte=today)
        
        if 'min_price' in self.request.query_params:
            queryset = queryset.filter(daily_price__gte=self.request.query_params['min_price'])
        
        if 'max_price' in self.request.query_params:
            queryset = queryset.filter(daily_price__lte=self.request.query_params['max_price'])
        
        if 'min_rating' in self.request.query_params:
            # Filter accommodations with average rating greater than or equal to min_rating
            min_rating = float(self.request.query_params['min_rating'])
            accommodation_ids = []
            for accommodation in queryset:
                if accommodation.average_rating >= min_rating:
                    accommodation_ids.append(accommodation.id)
            queryset = queryset.filter(id__in=accommodation_ids)
        
        if 'min_beds' in self.request.query_params:
            queryset = queryset.filter(beds__gte=self.request.query_params['min_beds'])
        
        if 'address_contains' in self.request.query_params:
            search_term = self.request.query_params['address_contains']
            queryset = queryset.filter(
                Q(address__icontains=search_term) | 
                Q(geo_address__icontains=search_term)
            )
            
        return queryset
    
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Custom search endpoint for accommodations with advanced filtering.
        
        Query Parameters:
        - type: Filter by accommodation type
        - min_beds/exact_beds: Filter by number of beds (minimum or exact)
        - min_bedrooms/exact_bedrooms: Filter by number of bedrooms (minimum or exact)
        - min_rating/exact_rating: Filter by rating (minimum or exact)
        - max_price: Filter by maximum price
        - available_from: Filter by availability start date
        - available_until: Filter by availability end date
        - distance_from: Calculate distances from specified HKU location or address
        
        Returns:
            Response: JSON response containing filtered accommodations with optional distance calculations
        """
        print("Search function reached")   
        query = Accommodation.objects.all()
        accommodation_type = request.GET.get('type')
        min_beds = request.GET.get('min_beds')
        exact_beds = request.GET.get('beds')
        min_bedrooms = request.GET.get('min_bedrooms')
        exact_bedrooms = request.GET.get('bedrooms')
        min_rating = request.GET.get('min_rating')
        exact_rating = request.GET.get('rating')
        max_price = request.GET.get('max_price')
        available_from = request.GET.get('available_from')
        available_until = request.GET.get('available_until')
        distance_from = request.GET.get('distance_from')  # Building name
        selected = {
            "Main Campus": (22.28405, 114.13784),
            "Sassoon Road Campus": (22.2675, 114.12881),
            "Swire Institute of Marine Science": (22.20805, 114.26021),
            "Kadoorie Centre": (22.43022, 114.11429),
            "Faculty of Dentistry": (22.28649, 114.14426),
        }
        R = 6371 

        if accommodation_type:
            query = query.filter(type=accommodation_type)
        
        if min_beds:
            query = query.filter(beds__gte=int(min_beds))#>=
        
        if exact_beds: #exact beds
            query = query.filter(beds=int(exact_beds)) 
        
        if min_bedrooms:
            query = query.filter(bedrooms__gte= int(min_bedrooms)) #>=
        
        if exact_bedrooms: #exact bedrooms
            query = query.filter(bedrooms=int(exact_bedrooms)) #exact bedrooms
        
        if available_from:
            query = query.filter(available_from__gte=datetime.strptime(available_from, "%Y-%m-%d")) #>=

        if available_until:
            query = query.filter(available_until__lte=datetime.strptime(available_until, "%Y-%m-%d")) #<=

        # Handle rating filtering based on average_rating property
        filtered_accommodations = list(query)
        if min_rating:
            min_rating_value = float(min_rating)
            filtered_accommodations = [acc for acc in filtered_accommodations if acc.average_rating >= min_rating_value]
            
        if exact_rating:
            exact_rating_value = float(exact_rating)
            filtered_accommodations = [acc for acc in filtered_accommodations if round(acc.average_rating) == exact_rating_value]
    
        if max_price:
            query = query.filter(daily_price__lte=Decimal(max_price)) #<=
            filtered_accommodations = list(query)

        if distance_from:
            if distance_from in selected:
                ref_lat, ref_lon = selected[distance_from]
            else:
                ref_lat, ref_lon, _ = geocode_address(distance_from)
            if ref_lat is not None and ref_lon is not None:
                accommodations_with_distance = []
                for accommodation in filtered_accommodations:
                    if accommodation.latitude is None or accommodation.longitude is None:
                        continue  

                    lat1, lon1 = math.radians(ref_lat), math.radians(ref_lon)
                    lat2, lon2 = math.radians(accommodation.latitude), math.radians(accommodation.longitude)
                    x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
                    y = (lat2 - lat1)
                    d = math.sqrt(x*x + y*y) * R 
                    accommodations_with_distance.append((d, accommodation))

                accommodations_with_distance.sort(key=lambda item: item[0])
                results = []
                for d, acc in accommodations_with_distance:
                    results.append({
                        'id': acc.id,
                        'type': acc.type,
                        'address': acc.address,
                        'beds': acc.beds,
                        'bedrooms': acc.bedrooms,
                        'average_rating': acc.average_rating,
                        'daily_price': acc.daily_price,
                        'available_from': acc.available_from,
                        'available_until': acc.available_until,
                        'distance_km': round(d, 2),
                    })
            else:
                results = {"error": "Invalid location specified"}
        else:
            results = []
            for acc in filtered_accommodations:
                results.append({
                    'id': acc.id,
                    'type': acc.type,
                    'address': acc.address,
                    'beds': acc.beds,
                    'bedrooms': acc.bedrooms,
                    'average_rating': acc.average_rating,
                    'daily_price': acc.daily_price,
                    'available_from': acc.available_from,
                    'available_until': acc.available_until,
                })
        
        return Response(results)
    
    def perform_create(self, serializer):
        """
        Create a new accommodation and geocode its address.
        
        Args:
            serializer: The serializer instance containing the accommodation data
            
        Returns:
            Accommodation: The created accommodation instance with geocoded coordinates
        """
        # First save the accommodation with the provided data
        accommodation = serializer.save()
        
        # Then attempt to geocode the address
        if accommodation.address:
            lat, lng, geo = geocode_address(accommodation.address)
            if lat is not None and lng is not None and geo is not None:
                accommodation.latitude = lat
                accommodation.longitude = lng
                accommodation.geo_address = geo
                accommodation.save()
                
        return accommodation
        
    def perform_update(self, serializer):
        """
        Update an accommodation and geocode its address if changed.
        
        Args:
            serializer: The serializer instance containing the updated accommodation data
            
        Returns:
            Accommodation: The updated accommodation instance with geocoded coordinates
        """
        # Check if address has changed
        if serializer.instance.address != serializer.validated_data.get('address', serializer.instance.address):
            # Save first to update the address
            accommodation = serializer.save()
            
            # Then geocode the new address
            lat, lng, geo = geocode_address(accommodation.address)
            if lat is not None and lng is not None and geo is not None:
                accommodation.latitude = lat
                accommodation.longitude = lng
                accommodation.geo_address = geo
                accommodation.save()
        else:
            # No address change, just save normally
            accommodation = serializer.save()
            
        return accommodation

class HKUMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing HKU members.
    Provides CRUD operations for HKUMember model.
    """
    queryset = HKUMember.objects.all()
    serializer_class = HKUMemberSerializer
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'reserve_accommodation':
            from .serializers import ReserveAccommodationSerializer
            return ReserveAccommodationSerializer
        elif self.action == 'cancel_reservation':
            from .serializers import CancelReservationSerializer
            return CancelReservationSerializer
        elif self.action == 'rate_accommodation':
            from .serializers import RateAccommodationSerializer
            return RateAccommodationSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        """
        Since authentication is handled by the CEDARS frontend, 
        we're using AllowAny permission and filtering based on role header/parameter.
        """
        return [permissions.AllowAny()]
    
    @action(detail=True, methods=['get'])
    def reservations(self, request, pk=None):
        """
        Get all reservations for a specific HKU member.
        
        Args:
            request: The HTTP request
            pk: The primary key of the HKU member
            
        Returns:
            Response: List of reservations for the member
        """
        # Check if role parameter is provided
        role = request.query_params.get('role', None)
        
        # If not a CEDARS specialist or the member themselves, return 403
        if role != 'cedars_specialist' and pk != request.query_params.get('current_user_id', None):
            return Response({"error": "You don't have permission to view these reservations"}, 
                          status=status.HTTP_403_FORBIDDEN)
            
        member = self.get_object()
        reservations = Reservation.objects.filter(member=member)
        
        # Filter by status if provided
        status_filter = request.query_params.get('status', None)
        if status_filter:
            reservations = reservations.filter(status=status_filter)
            
        # Order by start date descending (most recent first)
        reservations = reservations.order_by('-start_date')
        
        serializer = ReservationSerializer(reservations, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get', 'post'])
    def reserve_accommodation(self, request, pk=None):
        """
        Reserve an accommodation for a specific HKU member.
        
        Args:
            request: The HTTP request containing accommodation_id, start_date, end_date
            pk: The primary key of the HKU member
            
        Returns:
            Response: The created reservation or error message
        """
        # For GET requests, just display the form with correct fields
        if request.method == 'GET':
            # Use the serializer to display the correct form fields
            serializer = self.get_serializer()
            return Response(serializer.data)
            
        # Check if HKU member or CEDARS specialist role
        role = request.query_params.get('role', None)
        current_user_id = request.query_params.get('current_user_id', None)
        
        # Only allow if current user is this member or a CEDARS specialist
        if role != 'cedars_specialist' and (role != 'hku_member' or pk != current_user_id):
            return Response(
                {"error": "You don't have permission to make reservations for this member"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate the request data
        accommodation_id = request.data.get('accommodation_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not all([accommodation_id, start_date, end_date]):
            return Response(
                {"error": "accommodation_id, start_date, and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Auto-create the HKU member if they don't exist yet
        try:
            member = self.get_object()
        except Exception:
            if pk == current_user_id and role == 'hku_member':
                # Create the member with the provided UID
                name = request.data.get('member_name', f"HKU Member {pk}")
                member = HKUMember.objects.create(uid=pk, name=name)
            else:
                return Response(
                    {"error": "HKU member not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
        try:
            reservation = member.reserveAccommodation(
                accommodation_id=accommodation_id,
                start_date=start_date,
                end_date=end_date
            )
            serializer = ReservationSerializer(reservation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=True, methods=['get', 'post'])
    def cancel_reservation(self, request, pk=None):
        """
        Cancel a reservation for a specific HKU member.
        
        Args:
            request: The HTTP request containing reservation_id
            pk: The primary key of the HKU member
            
        Returns:
            Response: The cancelled reservation or error message
        """
        # For GET requests, just display the form with correct fields
        if request.method == 'GET':
            # Use the serializer to display the correct form fields
            serializer = self.get_serializer()
            return Response(serializer.data)
            
        # Check if HKU member or CEDARS specialist role
        role = request.query_params.get('role', None)
        current_user_id = request.query_params.get('current_user_id', None)
        
        # Only allow if current user is this member or a CEDARS specialist
        if role != 'cedars_specialist' and (role != 'hku_member' or pk != current_user_id):
            return Response(
                {"error": "You don't have permission to cancel reservations for this member"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        member = self.get_object()
        reservation_id = request.data.get('reservation_id')
        
        if not reservation_id:
            return Response(
                {"error": "reservation_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            reservation = member.cancelReservation(reservation_id=reservation_id)
            serializer = ReservationSerializer(reservation)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=True, methods=['get', 'post'])
    def rate_accommodation(self, request, pk=None):
        """
        Rate an accommodation based on a reservation.
        
        Args:
            request: The HTTP request containing reservation_id, score, and optional comment
            pk: The primary key of the HKU member
            
        Returns:
            Response: The created rating or error message
        """
        # For GET requests, just display the form with correct fields
        if request.method == 'GET':
            # Use the serializer to display the correct form fields
            serializer = self.get_serializer()
            return Response(serializer.data)
            
        # Check if HKU member role
        role = request.query_params.get('role', None)
        current_user_id = request.query_params.get('current_user_id', None)
        
        # Only allow if current user is this member
        if role != 'hku_member' or pk != current_user_id:
            return Response(
                {"error": "You don't have permission to rate accommodations for this member"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        member = self.get_object()
        reservation_id = request.data.get('reservation_id')
        score = request.data.get('score')
        comment = request.data.get('comment')
        
        if not all([reservation_id, score]):
            return Response(
                {"error": "reservation_id and score are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            rating = member.rateAccommodation(
                reservation_id=reservation_id,
                score=int(score),
                comment=comment
            )
            serializer = RatingSerializer(rating)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CEDARSSpecialistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing CEDARS specialists.
    Provides CRUD operations for CEDARSSpecialist model.
    """
    queryset = CEDARSSpecialist.objects.all()
    serializer_class = CEDARSSpecialistSerializer
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'add_accommodation':
            from .serializers import AccommodationSerializer
            return AccommodationSerializer
        elif self.action == 'update_accommodation':
            from .serializers import UpdateAccommodationSerializer
            return UpdateAccommodationSerializer
        elif self.action == 'cancel_reservation':
            from .serializers import CancelReservationSerializer
            return CancelReservationSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        """
        Since authentication is handled by the CEDARS frontend, 
        we're using AllowAny permission and filtering based on role header/parameter.
        """
        return [permissions.AllowAny()]
    
    @action(detail=True, methods=['get'])
    def managed_accommodations(self, request, pk=None):
        """
        Get all accommodations managed by a specific CEDARS specialist.
        
        Args:
            request: The HTTP request
            pk: The primary key of the CEDARS specialist
            
        Returns:
            Response: List of accommodations managed by the specialist
        """
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can view managed accommodations"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        specialist = self.get_object()
        accommodations = Accommodation.objects.filter(specialist=specialist)
        serializer = AccommodationSerializer(accommodations, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['get', 'post'])
    def add_accommodation(self, request, pk=None):
        """
        Add a new accommodation managed by this specialist.
        
        Args:
            request: The HTTP request containing accommodation data
            pk: The primary key of the CEDARS specialist
            
        Returns:
            Response: The created accommodation or error message
        """
        # For GET requests, just display the form with correct fields
        if request.method == 'GET':
            # Use the serializer to display the correct form fields
            serializer = self.get_serializer()
            return Response(serializer.data)
            
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can add accommodations"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        specialist = self.get_object()
        # Add specialist to the request data
        request.data['specialist_id'] = specialist.id
        
        serializer = AccommodationSerializer(data=request.data)
        if serializer.is_valid():
            accommodation = specialist.addAccommodation(serializer.validated_data)
            result_serializer = AccommodationSerializer(accommodation)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['get', 'post'])
    def update_accommodation(self, request, pk=None):
        """
        Update an existing accommodation managed by this specialist.
        
        Args:
            request: The HTTP request containing accommodation_id and updated data
            pk: The primary key of the CEDARS specialist
            
        Returns:
            Response: The updated accommodation or error message
        """
        # For GET requests, just display the form with correct fields
        if request.method == 'GET':
            # Use the serializer to display the correct form fields
            serializer = self.get_serializer()
            return Response(serializer.data)
            
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can update accommodations"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        specialist = self.get_object()
        accommodation_id = request.data.get('accommodation_id')
        
        if not accommodation_id:
            return Response(
                {"error": "accommodation_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Remove accommodation_id from the data to update
            update_data = request.data.copy()
            update_data.pop('accommodation_id')
            
            accommodation = specialist.updateAccommodation(
                accommodation_id=accommodation_id,
                updated_data=update_data
            )
            serializer = AccommodationSerializer(accommodation)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get', 'post'])
    def cancel_reservation(self, request, pk=None):
        """
        Cancel a reservation as a CEDARS specialist.
        
        Args:
            request: The HTTP request containing reservation_id
            pk: The primary key of the CEDARS specialist
            
        Returns:
            Response: The cancelled reservation or error message
        """
        # For GET requests, just display the form with correct fields
        if request.method == 'GET':
            # Use the serializer to display the correct form fields
            serializer = self.get_serializer()
            return Response(serializer.data)
            
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can cancel reservations from this endpoint"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        specialist = self.get_object()
        reservation_id = request.data.get('reservation_id')
        
        if not reservation_id:
            return Response(
                {"error": "reservation_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            reservation = specialist.cancelReservation(reservation_id=reservation_id)
            serializer = ReservationSerializer(reservation)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reservations.
    Provides CRUD operations for Reservation model.
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'confirm':
            from .serializers import ConfirmReservationSerializer
            return ConfirmReservationSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        """
        Since authentication is handled by the CEDARS frontend, 
        we're using AllowAny permission and filtering based on role header/parameter.
        """
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        """
        Get filtered queryset based on query parameters and role.
        
        Available filters:
        - member_id: Filter by HKU member
        - accommodation_id: Filter by accommodation
        - status: Filter by reservation status
        
        Returns:
            QuerySet: Filtered queryset of reservations
        """
        queryset = super().get_queryset()
        
        # Get role from query parameters
        role = self.request.query_params.get('role', None)
        current_user_id = self.request.query_params.get('current_user_id', None)
        
        # If HKU member role, only show their own reservations
        if role == 'hku_member' and current_user_id:
            queryset = queryset.filter(member__uid=current_user_id)
        # If not CEDARS specialist, limit access
        elif role != 'cedars_specialist':
            if self.action == 'list':
                # Empty queryset for non-specialists
                queryset = Reservation.objects.none()
        
        # Apply other filters
        if 'member_id' in self.request.query_params:
            queryset = queryset.filter(member__uid=self.request.query_params['member_id'])
            
        if 'accommodation_id' in self.request.query_params:
            queryset = queryset.filter(accommodation_id=self.request.query_params['accommodation_id'])
            
        if 'status' in self.request.query_params:
            queryset = queryset.filter(status=self.request.query_params['status'])
            
        return queryset
    
    @action(detail=True, methods=['get', 'post'])
    def confirm(self, request, pk=None):
        """
        Confirm a reservation, changing its status from 'pending' to 'confirmed'.
        
        Args:
            request: The HTTP request
            pk: The primary key of the reservation
            
        Returns:
            Response: The updated reservation or error message
        """
        # For GET requests, just display a form with confirmation message
        if request.method == 'GET':
            # Use the serializer to display the correct form fields
            serializer = self.get_serializer()
            return Response(serializer.data)
            
        # Check if CEDARS specialist role
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can confirm reservations"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        reservation = self.get_object()
        
        if reservation.status != 'pending':
            return Response(
                {"error": f"Cannot confirm reservation with status '{reservation.status}'. Only pending reservations can be confirmed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = reservation.status
        reservation.status = 'confirmed'
        reservation.save()
        
        # Send reservation update notification
        from unihaven.utils.notifications import send_reservation_update
        send_reservation_update(reservation, old_status)
        
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)

class RatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ratings.
    Provides CRUD operations for Rating model.
    """
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    
    def get_permissions(self):
        """
        Since authentication is handled by the CEDARS frontend, 
        we're using AllowAny permission and filtering based on role header/parameter.
        """
        return [permissions.AllowAny()]
    
    def create(self, request, *args, **kwargs):
        """
        Create a new rating.
        Only HKU members can create ratings for their own completed reservations.
        """
        # Check if HKU member role
        role = request.query_params.get('role', None)
        current_user_id = request.query_params.get('current_user_id', None)
        
        if role != 'hku_member' or not current_user_id:
            return Response(
                {"error": "Only HKU members can create ratings"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check if the reservation belongs to the current user
        reservation_id = request.data.get('reservation')
        if not reservation_id:
            return Response(
                {"error": "reservation_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            reservation = Reservation.objects.get(id=reservation_id)
            if reservation.member.uid != current_user_id:
                return Response(
                    {"error": "You can only rate your own reservations"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            if reservation.status != 'completed':
                return Response(
                    {"error": "You can only rate completed reservations"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Reservation.DoesNotExist:
            return Response(
                {"error": "Reservation not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """
        Update a rating.
        HKU members can only update their own ratings.
        CEDARS specialists can update any rating.
        """
        # Check user role
        role = request.query_params.get('role', None)
        current_user_id = request.query_params.get('current_user_id', None)
        
        if role == 'cedars_specialist':
            # CEDARS specialists can update any rating
            pass
        elif role == 'hku_member' and current_user_id:
            # HKU members can only update their own ratings
            rating = self.get_object()
            if rating.reservation.member.uid != current_user_id:
                return Response(
                    {"error": "You can only update your own ratings"},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {"error": "You don't have permission to update ratings"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a rating.
        HKU members can delete their own ratings.
        CEDARS specialists can delete any rating.
        """
        # Check user role
        role = request.query_params.get('role', None)
        current_user_id = request.query_params.get('current_user_id', None)
        
        if role == 'cedars_specialist':
            # CEDARS specialists can delete any rating
            pass
        elif role == 'hku_member' and current_user_id:
            # HKU members can only delete their own ratings
            rating = self.get_object()
            if rating.reservation.member.uid != current_user_id:
                return Response(
                    {"error": "You can only delete your own ratings"},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {"error": "You don't have permission to delete ratings"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        return super().destroy(request, *args, **kwargs)
    
    def get_queryset(self):
        """
        Get filtered queryset based on query parameters.
        
        Available filters:
        - reservation_id: Filter by reservation
        - accommodation_id: Filter by accommodation (via reservation)
        - member_id: Filter by HKU member (via reservation)
        
        Returns:
            QuerySet: Filtered queryset of ratings
        """
        queryset = super().get_queryset()
        
        if 'reservation_id' in self.request.query_params:
            queryset = queryset.filter(reservation_id=self.request.query_params['reservation_id'])
            
        if 'accommodation_id' in self.request.query_params:
            queryset = queryset.filter(reservation__accommodation_id=self.request.query_params['accommodation_id'])
            
        if 'member_id' in self.request.query_params:
            queryset = queryset.filter(reservation__member__uid=self.request.query_params['member_id'])
            
        return queryset

@api_view(['GET', 'POST'])
def add_accommodation(request):
    """
    API endpoint for adding new accommodations.
    
    Methods:
        GET: Returns an empty serializer for form rendering
        POST: Creates a new accommodation with geocoded address
        
    Args:
        request: The HTTP request object
        
    Returns:
        Response: 
            - GET: Empty serializer data
            - POST: Created accommodation data or validation errors
    """
    # Check if CEDARS specialist role for POST
    if request.method == 'POST':
        role = request.query_params.get('role', None)
        if role != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS specialists can add accommodations"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = AccommodationSerializer(data=request.data)
        if serializer.is_valid():
            # First save the accommodation with the provided data
            accommodation = serializer.save()
            
            # Then attempt to geocode the address
            if accommodation.address:
                lat, lng, geo = geocode_address(accommodation.address)
                if lat is not None and lng is not None and geo is not None:
                    accommodation.latitude = lat
                    accommodation.longitude = lng
                    accommodation.geo_address = geo
                    accommodation.save()
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        # For GET requests, just return an empty serializer to render the form
        serializer = AccommodationSerializer()
        return Response(serializer.initial_data)