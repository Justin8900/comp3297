from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q, Avg
from rest_framework import viewsets, status, filters, permissions
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes, renderer_classes
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from datetime import datetime
from decimal import Decimal
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from .models import *
from .serializers import (
    PropertyOwnerSerializer, AccommodationSerializer, HKUMemberSerializer,
    CEDARSSpecialistSerializer, ReservationSerializer, RatingSerializer,
    ReserveAccommodationSerializer, CancelReservationSerializer, RateAccommodationSerializer,
    ConfirmReservationSerializer, AccommodationSearchSerializer, UpdateAccommodationSerializer
)
from .permissions import (
    IsAnyCEDARSSpecialist, 
    IsAnyHKUMemberOrCEDARSSpecialist,
    CanRetrieveUpdateHKUMember,
    CanListReservations,
    CanCreateReservation,
    CanAccessReservationObject,
    CanListRatings,
    CanCreateRating,
    CanAccessRatingObject,
    get_role_and_id_from_request
)
from .utils.geocoding import geocode_address
import math

# API Views
@extend_schema_view(
    list=extend_schema(
        summary="List property owners (Specialists Only)",
        description="List all property owners. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    create=extend_schema(
        summary="Create property owner (Specialists Only)",
        description="Create a new property owner. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Retrieve property owner (Specialists Only)", 
        description="Retrieve details of a specific property owner. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    update=extend_schema(
        summary="Update property owner (Specialists Only)",
        description="Update a property owner. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    partial_update=extend_schema(
        summary="Partially update property owner (Specialists Only)",
        description="Partially update a property owner. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    destroy=extend_schema(
        summary="Delete property owner (Specialists Only)",
        description="Delete a property owner. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    )
)
class PropertyOwnerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing property owners.
    Provides CRUD operations for PropertyOwner model.
    Requires CEDARS Specialist role for all actions.
    """
    queryset = PropertyOwner.objects.all().order_by('id')
    serializer_class = PropertyOwnerSerializer
    permission_classes = [IsAnyCEDARSSpecialist]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
        
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
        
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
        
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True 
        return super().update(request, *args, **kwargs)
        
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
        

@extend_schema_view(
    list=extend_schema(
        summary="List all accommodations",
        description="List all accommodations. Accessible by both HKU members and CEDARS specialists.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (format: 'hku_member:uid' or 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    create=extend_schema(
        summary="Create accommodation (Specialists Only)",
        description="Create a new accommodation listing. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Retrieve an accommodation",
        description="Retrieve details for a specific accommodation. Accessible by both HKU members and CEDARS specialists.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (format: 'hku_member:uid' or 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    update=extend_schema(
        summary="Update accommodation (Specialists Only)",
        description="Update an accommodation listing. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    partial_update=extend_schema(
        summary="Partially update accommodation (Specialists Only)",
        description="Partially update an accommodation listing. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    destroy=extend_schema(
        summary="Delete accommodation (Specialists Only)",
        description="Delete an accommodation listing. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    )
)
class AccommodationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing accommodations.
    """
    queryset = Accommodation.objects.all().order_by('id')
    serializer_class = AccommodationSerializer
    permission_classes = [IsAnyHKUMemberOrCEDARSSpecialist]

    def get_permissions(self):
        base_perms = []
        if self.action in ['list', 'retrieve', 'search']:
            role_perms = [IsAnyHKUMemberOrCEDARSSpecialist]
        elif self.action in ['create', 'update', 'partial_update', 'destroy', 'reservations']:
            role_perms = [IsAnyCEDARSSpecialist]
        else:
            role_perms = [permissions.IsAdminUser]
        return [permission() for permission in base_perms + role_perms]
    
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
        
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        accommodation = serializer.instance
        if accommodation.address:
            try:
                lat, lng, geo = geocode_address(accommodation.address)
                if lat is not None and lng is not None and geo is not None:
                    accommodation.latitude = lat
                    accommodation.longitude = lng
                    accommodation.geo_address = geo
                    accommodation.save(update_fields=['latitude', 'longitude', 'geo_address'])
            except Exception as e:
                print(f"Geocoding failed for address {accommodation.address}: {e}") 
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        address_changed = 'address' in serializer.validated_data and serializer.validated_data['address'] != instance.address
        self.perform_update(serializer)
        if address_changed:
            accommodation = serializer.instance
            if accommodation.address:
                try:
                    lat, lng, geo = geocode_address(accommodation.address)
                    if lat is not None and lng is not None and geo is not None:
                        accommodation.latitude = lat
                        accommodation.longitude = lng
                        accommodation.geo_address = geo
                        accommodation.save(update_fields=['latitude', 'longitude', 'geo_address'])
                except Exception as e:
                    print(f"Geocoding failed during update for address {accommodation.address}: {e}")
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()
        
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
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
    
    @extend_schema(
        summary="Search for accommodations",
        description="Custom search endpoint for accommodations with advanced filtering. Accessible by both HKU members and CEDARS specialists.",
        parameters=[
            OpenApiParameter(name="role", description="User role (format: 'hku_member:uid' or 'cedars_specialist[:id]')", required=True, type=str),
            OpenApiParameter(name="type", description="Filter by accommodation type (e.g., 'apartment', 'house')", type=str),
            OpenApiParameter(name="min_beds", description="Filter by minimum number of beds", type=OpenApiTypes.INT),
            OpenApiParameter(name="beds", description="Filter by exact number of beds", type=OpenApiTypes.INT),
            OpenApiParameter(name="min_bedrooms", description="Filter by minimum number of bedrooms", type=OpenApiTypes.INT),
            OpenApiParameter(name="bedrooms", description="Filter by exact number of bedrooms", type=OpenApiTypes.INT),
            OpenApiParameter(name="min_rating", description="Filter by minimum average rating (e.g., 4.0)", type=OpenApiTypes.FLOAT),
            OpenApiParameter(name="rating", description="Filter by exact average rating (e.g., 4.5)", type=OpenApiTypes.FLOAT),
            OpenApiParameter(name="max_price", description="Filter by maximum daily price", type=OpenApiTypes.FLOAT),
            OpenApiParameter(name="available_from", description="Filter by availability start date (YYYY-MM-DD)", type=OpenApiTypes.DATE),
            OpenApiParameter(name="available_until", description="Filter by availability end date (YYYY-MM-DD)", type=OpenApiTypes.DATE),
            OpenApiParameter(name="distance_from", description="Calculate and sort by distance from a specified HKU location (e.g., 'Main Campus', 'Sassoon Road') or address", type=str),
        ],
        responses={200: AccommodationSerializer(many=True)} # Response structure depends on distance_from
    )
    @action(detail=False, methods=['get'], url_path='search', permission_classes=[IsAnyHKUMemberOrCEDARSSpecialist])
    def search(self, request):
        queryset = Accommodation.objects.all().order_by('id')
        
        if 'type' in request.query_params:
            queryset = queryset.filter(type=request.query_params['type'])
            
        if 'min_beds' in request.query_params:
            queryset = queryset.filter(beds__gte=int(request.query_params['min_beds']))
            
        if 'beds' in request.query_params:
            queryset = queryset.filter(beds=int(request.query_params['beds']))
            
        if 'min_bedrooms' in request.query_params:
            queryset = queryset.filter(bedrooms__gte=int(request.query_params['min_bedrooms']))
            
        if 'bedrooms' in request.query_params:
            queryset = queryset.filter(bedrooms=int(request.query_params['bedrooms']))
            
        if 'max_price' in request.query_params:
            queryset = queryset.filter(daily_price__lte=float(request.query_params['max_price']))
            
        today = datetime.now().date()
        
        if 'available_from' in request.query_params:
            try:
                available_from = datetime.strptime(request.query_params['available_from'], '%Y-%m-%d').date()
                queryset = queryset.filter(available_from__lte=available_from, available_until__gte=available_from)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        if 'available_until' in request.query_params:
            try:
                available_until = datetime.strptime(request.query_params['available_until'], '%Y-%m-%d').date()
                queryset = queryset.filter(available_from__lte=available_until, available_until__gte=available_until)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        filtered_accommodations = list(queryset)
        
        if 'min_rating' in request.query_params:
            min_rating = float(request.query_params['min_rating'])
            filtered_accommodations = [acc for acc in filtered_accommodations if acc.average_rating >= min_rating]
            
        if 'rating' in request.query_params:
            rating = float(request.query_params['rating'])
            filtered_accommodations = [acc for acc in filtered_accommodations if abs(acc.average_rating - rating) < 0.1]
        
        if 'distance_from' in request.query_params:
            from unihaven.utils.geocoding import get_hku_location, calculate_distance
            
            location_name = request.query_params.get('distance_from', '')
            source_lat, source_lng = get_hku_location(location_name)
            
            if source_lat is None or source_lng is None:
                return Response(
                    {"error": f"Unknown location: {location_name}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            results = []
            for acc in filtered_accommodations:
                if acc.latitude is not None and acc.longitude is not None:
                    distance = calculate_distance(source_lat, source_lng, acc.latitude, acc.longitude)
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
                        'distance_km': round(distance, 2)
                    })
            
            results.sort(key=lambda x: x['distance_km'])
            
            return Response(results)
        
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

@extend_schema_view(
    list=extend_schema(
        summary="List HKU members (Specialists Only)",
        description="List all HKU members. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    create=extend_schema(
        summary="Create HKU member (Specialists Only)",
        description="Create a new HKU member. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Retrieve a HKU member", 
        description="Retrieve a HKU member by UID. CEDARS specialists can retrieve any member. HKU members can only retrieve their own details (matching UID in role).",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]') identifying the requester.", 
                required=True,
                type=str
            )
        ]
    ),
    update=extend_schema(
        summary="Update a HKU member",
        description="Update a HKU member by UID. CEDARS specialists can update any member. HKU members can only update their own details (matching UID in role).",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]') identifying the requester.", 
                required=True,
                type=str
            )
        ]
    ),
    partial_update=extend_schema(
        summary="Partially update a HKU member",
        description="Partially update a HKU member by UID. CEDARS specialists can update any member. HKU members can only update their own details (matching UID in role).",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]') identifying the requester.", 
                required=True,
                type=str
            )
        ]
    ),
    destroy=extend_schema(
        summary="Delete HKU member (Specialists Only)",
        description="Delete a HKU member by UID. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    )
)
class HKUMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing HKU members.
    """
    queryset = HKUMember.objects.all()
    serializer_class = HKUMemberSerializer
    lookup_field = 'uid'

    def get_permissions(self):
        base_perms = []
        if self.action in ['list', 'create', 'destroy']:
            role_perms = [IsAnyCEDARSSpecialist]
        elif self.action in ['retrieve', 'update', 'partial_update', 'reservations']:
            role_perms = [CanRetrieveUpdateHKUMember]
        else:
            role_perms = [permissions.IsAdminUser]
        return [permission() for permission in base_perms + role_perms]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
        
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
        
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
        
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
        
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)
        
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
        
    @extend_schema(
        summary="List reservations for a HKU member",
        description="Get all reservations for a specific HKU member (identified by UID in URL).\nHKU members can only view their own reservations (matching UID in role). CEDARS specialists can view any HKU member's reservations.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist:id') identifying the requester.", 
                required=True,
                type=str
            ),
            OpenApiParameter(
                name="status", 
                description="Filter reservations by status", 
                required=False,
                type=str,
                enum=["pending", "confirmed", "cancelled", "completed"]
            )
        ],
        responses={
            200: ReservationSerializer(many=True),
            403: OpenApiTypes.OBJECT
        }
    )
    @action(detail=True, methods=['get'], permission_classes=[CanRetrieveUpdateHKUMember])
    def reservations(self, request, uid=None):
        member = self.get_object()
        reservations = Reservation.objects.filter(member=member)
        
        if 'status' in request.query_params:
            reservations = reservations.filter(status=request.query_params['status'])
            
        serializer = ReservationSerializer(reservations, many=True)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        summary="List CEDARS specialists (Specialists Only)",
        description="List all CEDARS specialists. Only CEDARS specialists can perform this action.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    create=extend_schema(
        summary="Create CEDARS specialist (Specialists Only)",
        description="Create a new CEDARS specialist. Only CEDARS specialists can create new specialists.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Retrieve CEDARS specialist (Specialists Only)",
        description="Retrieve a CEDARS specialist by ID. Only CEDARS specialists can view specialist details.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    update=extend_schema(
        summary="Update CEDARS specialist (Specialists Only)",
        description="Update a CEDARS specialist by ID. Only CEDARS specialists can update specialists.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    partial_update=extend_schema(
        summary="Partially update CEDARS specialist (Specialists Only)",
        description="Partially update a CEDARS specialist by ID. Only CEDARS specialists can update specialists.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    destroy=extend_schema(
        summary="Delete CEDARS specialist (Specialists Only)",
        description="Delete a CEDARS specialist by ID. Only CEDARS specialists can delete specialists.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    )
)
class CEDARSSpecialistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing CEDARS specialists.
    Requires CEDARS Specialist role for all actions.
    """
    queryset = CEDARSSpecialist.objects.all().order_by('id')
    serializer_class = CEDARSSpecialistSerializer
    permission_classes = [IsAnyCEDARSSpecialist]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

@extend_schema_view(
    list=extend_schema(
        summary="List reservations (Specialists Only)",
        description="List all reservations. Only CEDARS specialists can list all reservations. HKU members should use `/hku-members/{uid}/reservations/`. Uses manual role check.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            ),
            OpenApiParameter(
                name="member_id", 
                description="Filter by HKU member UID", 
                required=False,
                type=str
            ),
            OpenApiParameter(
                name="accommodation_id", 
                description="Filter by accommodation ID", 
                required=False,
                type=int
            ),
            OpenApiParameter(
                name="status", 
                description="Filter by reservation status", 
                required=False,
                type=str,
                enum=["pending", "confirmed", "cancelled", "completed"]
            )
        ]
    ),
    create=extend_schema(exclude=True), # Exclude standard POST, use custom action
    retrieve=extend_schema(
        summary="Retrieve a reservation",
        description="Retrieve details of a specific reservation. HKU members can only retrieve their own reservations. CEDARS specialists can retrieve any reservation. Uses manual role check.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]') identifying the requester.", 
                required=True,
                type=str
            )
        ]
    ),
    update=extend_schema(
        summary="Update reservation (Specialists Only)",
        description="Update a reservation. Only CEDARS specialists can perform this action. Uses manual role check.",
        parameters=[
            OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str)
        ]
    ),
    partial_update=extend_schema(exclude=True), # Excluded - Use PUT for updates
    destroy=extend_schema(
        summary="Delete reservation (Specialists Only)",
        description="Delete a reservation. Only CEDARS specialists can delete reservations. Uses manual role check.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    )
)
class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reservations.
    """
    queryset = Reservation.objects.all().order_by('-start_date')
    serializer_class = ReservationSerializer
    permission_classes = []

    @extend_schema(summary="List reservations (Specialists Only)", 
                   description="List all reservations. Only CEDARS specialists can list all reservations. HKU members should use `/hku-members/{uid}/reservations/`. Uses manual role check.",
                   parameters=[
                       OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str),
                       OpenApiParameter(name="member_id", description="Filter by HKU member UID", required=False, type=str),
                       OpenApiParameter(name="accommodation_id", description="Filter by accommodation ID", required=False, type=int),
                       OpenApiParameter(name="status", description="Filter by reservation status", required=False, type=str, enum=["pending", "confirmed", "cancelled", "completed"])
                   ])
    def list(self, request, *args, **kwargs):
        role_type, _ = get_role_and_id_from_request(request)
        if role_type != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS Specialists can list all reservations from this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.filter_queryset(self.get_queryset())
        
        if 'member_id' in request.query_params:
            queryset = queryset.filter(member__uid=request.query_params['member_id'])
        if 'accommodation_id' in request.query_params:
            queryset = queryset.filter(accommodation_id=request.query_params['accommodation_id'])
        if 'status' in request.query_params:
            queryset = queryset.filter(status=request.query_params['status'])
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        
    @extend_schema(summary="Retrieve a reservation",
                   description="Retrieve details of a specific reservation. HKU members can only retrieve their own reservations. CEDARS specialists can retrieve any reservation. Uses manual role check.",
                   parameters=[
                       OpenApiParameter(name="role", description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]')", required=True, type=str)
                   ])
    def retrieve(self, request, *args, **kwargs):
        # --- Manual Role Check (Object Level) ---
        role_type, role_id = get_role_and_id_from_request(request)
        if not role_type:
             return Response({"error": "Role query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
             
        instance = self.get_object() # Raises 404 if not found
        
        allowed = False
        if role_type == 'cedars_specialist':
            allowed = True
        elif role_type == 'hku_member' and role_id:
            if str(instance.member.uid) == str(role_id):
                allowed = True
                
        if not allowed:
            return Response(
                {"error": "You do not have permission to access this reservation."},
                status=status.HTTP_403_FORBIDDEN
            )
        # --- End Manual Role Check ---

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(exclude=True) # Standard POST is excluded, use custom action below
    def create(self, request, *args, **kwargs):
        return Response({"detail": "Method \"POST\" not allowed. Use /reservations/create/ instead."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
    @extend_schema(
        summary="Update reservation (Specialists Only)",
        description="Update a reservation. Only CEDARS specialists can perform this action. Uses manual role check.",
        parameters=[
            OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str)
        ]
    )
    def update(self, request, *args, **kwargs):
        # --- Manual Role Check ---
        role_type, _ = get_role_and_id_from_request(request)
        if role_type != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS Specialists can update reservations."},
                status=status.HTTP_403_FORBIDDEN
            )
        # --- End Manual Role Check ---
        
        # Standard update logic (from ModelViewSet)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Add validation to prevent overlap before saving
        accommodation_id = serializer.validated_data.get('accommodation', instance.accommodation_id)
        start_date = serializer.validated_data.get('start_date', instance.start_date)
        end_date = serializer.validated_data.get('end_date', instance.end_date)
        
        overlapping = Reservation.objects.filter(
            accommodation_id=accommodation_id,
            status__in=['pending', 'confirmed'],
            start_date__lt=end_date, 
            end_date__gt=start_date
        ).exclude(pk=instance.pk).exists() # Exclude self

        if overlapping:
            return Response({"error": "Updated dates overlap with an existing reservation for this accommodation."}, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @extend_schema(exclude=True) # Excluded - Use PUT for updates
    def partial_update(self, request, *args, **kwargs):
        # PATCH is disabled for now (returns 405)
        return Response({"detail": "Method \"PATCH\" not allowed. Use PUT for full updates."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(
        summary="Delete reservation (Specialists Only)",
        description="Delete a reservation. Only CEDARS specialists can delete reservations. Uses manual role check.",
        parameters=[
            OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str)
        ]
    )
    def destroy(self, request, *args, **kwargs):
        role_type, _ = get_role_and_id_from_request(request)
        if role_type != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS Specialists can delete reservations."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new reservation",
        description="Create a new reservation. HKU members use 'hku_member:uid' and the system uses the UID. CEDARS specialists use 'cedars_specialist[:id]' and must provide 'member_id' (HKU member UID) in the request body.",
        request=ReserveAccommodationSerializer,
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ],
        responses={201: ReservationSerializer}
    )
    @action(detail=False, methods=['post'], url_path='create', 
            authentication_classes=[], permission_classes=[]) # Manual checks inside
    def create_reservation(self, request, *args, **kwargs):
        role_type, role_id = get_role_and_id_from_request(request)
        if not role_type:
             return Response(
                 {"error": "Role query parameter is required."},
                 status=status.HTTP_400_BAD_REQUEST
             )

        member_uid = None
        if role_type == 'hku_member' and role_id:
            member_uid = role_id
        elif role_type == 'cedars_specialist':
            member_uid = request.data.get('member_id')
            if not member_uid:
                return Response(
                    {"error": "CEDARS specialists must specify a member_id in the request body when creating a reservation."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                 {"error": f"Invalid role specified: '{request.query_params.get('role')}'"},
                 status=status.HTTP_400_BAD_REQUEST
             )
        
        try:
            member = HKUMember.objects.get(uid=member_uid)
        except HKUMember.DoesNotExist:
            return Response({"error": f"HKU member with UID {member_uid} not found"}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = ReserveAccommodationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        accommodation_id = serializer.validated_data.get('accommodation_id')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')

        try:
            accommodation = Accommodation.objects.get(pk=accommodation_id)
        except Accommodation.DoesNotExist:
             return Response({"error": f"Accommodation with ID {accommodation_id} not found"}, status=status.HTTP_400_BAD_REQUEST)

        overlapping = Reservation.objects.filter(
            accommodation=accommodation,
            status__in=['pending', 'confirmed'],
            start_date__lt=end_date, 
            end_date__gt=start_date
        ).exists()

        if overlapping:
            return Response({"error": "Accommodation is not available for the selected dates."}, status=status.HTTP_400_BAD_REQUEST)
            
        reservation = Reservation.objects.create(
            status='pending',
            start_date=start_date,
            end_date=end_date,
            member=member, 
            accommodation=accommodation
        )
        
        response_serializer = ReservationSerializer(reservation)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="Cancel a reservation",
        description="Cancel an existing reservation. HKU members can cancel their own pending/confirmed reservations before the end date. CEDARS specialists can cancel any reservation. Uses manual role check.",
        request=None, # No request body expected for cancellation
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ],
        responses={200: ReservationSerializer, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    @action(detail=True, methods=['post'], url_path='cancel', 
            authentication_classes=[], permission_classes=[]) # Manual checks inside
    def cancel(self, request, pk=None):
        role_type, role_id = get_role_and_id_from_request(request)
        if not role_type:
             return Response(
                 {"error": "Role query parameter is required."},
                 status=status.HTTP_400_BAD_REQUEST
             )

        try:
            reservation = self.get_object()
        except Reservation.DoesNotExist:
             return Response(
                 {"error": "Reservation not found."},
                 status=status.HTTP_404_NOT_FOUND
             )

        allowed = False
        if role_type == 'cedars_specialist':
             allowed = True
        elif role_type == 'hku_member' and role_id:
             if hasattr(reservation, 'member') and str(reservation.member.uid) == str(role_id):
                 # Add check: Cannot cancel if reservation end date has passed
                 if reservation.end_date < datetime.now().date():
                     return Response({"error": "Cannot cancel a reservation whose end date has passed."}, status=status.HTTP_400_BAD_REQUEST)
                 reservation.status = 'cancelled'
                 reservation.save(update_fields=['status'])
                 print(f"Reservation {pk} cancelled by HKU Member {role_id}") # Debug
                 return Response({"status": f"Reservation {pk} cancelled successfully."}, status=status.HTTP_200_OK)
             else:
                 print(f"HKU Member {role_id} mismatch or no member associated with Reservation {pk}") # Debug
                 return Response({"error": "You can only cancel your own reservations."}, status=status.HTTP_403_FORBIDDEN)
        else:
             return Response(
                 {"error": f"Invalid role specified: '{request.query_params.get('role')}'"},
                 status=status.HTTP_400_BAD_REQUEST
             )
        
        if not allowed:
             return Response(
                 {"error": "You do not have permission to cancel this reservation."},
                 status=status.HTTP_403_FORBIDDEN
             )
        
        if reservation.status == 'cancelled':
            return Response(
                {"error": "Reservation is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reservation.status = 'cancelled'
        reservation.cancelled_by = role_type
        reservation.save(update_fields=['status', 'cancelled_by'])
        
        serializer = self.get_serializer(reservation)
        return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema_view(
    list=extend_schema(
        summary="List ratings",
        description="List ratings. CEDARS specialists can list all ratings and filter. HKU members can only list their own ratings. Uses manual role check.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]')", 
                required=True,
                type=str
            ),
            OpenApiParameter(
                name="reservation_id", 
                description="Filter by reservation ID", 
                required=False,
                type=int
            ),
            OpenApiParameter(
                name="accommodation_id", 
                description="Filter by accommodation ID", 
                required=False,
                type=int
            ),
            OpenApiParameter(
                name="member_id", 
                description="Filter by HKU member UID (only usable by CEDARS Specialists)", 
                required=False,
                type=str
            )
        ]
    ),
    create=extend_schema(exclude=True), # Standard POST is excluded, use custom action below
    retrieve=extend_schema(
        summary="Retrieve a rating",
        description="Retrieve details of a specific rating. HKU members can only retrieve ratings for their own reservations. CEDARS specialists can retrieve any rating. Uses manual role check.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]') identifying the requester.", 
                required=True,
                type=str
            )
        ]
    ),
    update=extend_schema(
        summary="Update rating (Specialists Only)",
        description="Update a rating. Only CEDARS specialists can perform this action. Uses manual role check.",
        parameters=[
            OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str)
        ]
    ),
    partial_update=extend_schema(
        summary="Partially update rating (Specialists Only)",
        description="Partially update a rating. Only CEDARS specialists can perform this action. Uses manual role check.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    ),
    destroy=extend_schema(
        summary="Delete rating (Specialists Only)",
        description="Delete a rating. Only CEDARS specialists can delete ratings. Uses manual role check.",
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role (must be 'cedars_specialist[:id]')", 
                required=True,
                type=str
            )
        ]
    )
)
class RatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ratings.
    """
    queryset = Rating.objects.all().select_related('reservation__member', 'reservation__accommodation').order_by('id')
    serializer_class = RatingSerializer

    @extend_schema(summary="List ratings",
                   description="List ratings. CEDARS specialists can list all ratings and filter. HKU members can only list their own ratings. Uses manual role check.",
                   parameters=[
                       OpenApiParameter(name="role", description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]')", required=True, type=str),
                       OpenApiParameter(name="reservation_id", description="Filter by reservation ID", required=False, type=int),
                       OpenApiParameter(name="accommodation_id", description="Filter by accommodation ID", required=False, type=int),
                       OpenApiParameter(name="member_id", description="Filter by HKU member UID (only usable by Specialists)", required=False, type=str)
                   ])
    def list(self, request, *args, **kwargs):
        role_type, role_id = get_role_and_id_from_request(request)
        if not role_type:
             return Response({"error": "Role query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
             
        queryset = self.get_queryset()
        
        if role_type == 'hku_member':
            if not role_id:
                 return Response({"error": "HKU member role requires a UID (hku_member:uid)."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(reservation__member__uid=role_id)
        elif role_type == 'cedars_specialist':
            # Specialists can filter by member_id if provided
            if 'member_id' in request.query_params:
                queryset = queryset.filter(reservation__member__uid=request.query_params['member_id'])
        else:
             return Response(
                 {"error": "Invalid role specified for listing ratings."}, 
                 status=status.HTTP_403_FORBIDDEN
             )
             
        # Common filters
        if 'reservation_id' in request.query_params:
            queryset = queryset.filter(reservation_id=request.query_params['reservation_id'])
        if 'accommodation_id' in request.query_params:
            queryset = queryset.filter(reservation__accommodation_id=request.query_params['accommodation_id'])
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        
    @extend_schema(summary="Retrieve a rating",
                   description="Retrieve details of a specific rating. HKU members can only retrieve ratings for their own reservations. CEDARS specialists can retrieve any rating. Uses manual role check.",
                   parameters=[
                       OpenApiParameter(name="role", description="User role with ID (format: 'hku_member:uid' or 'cedars_specialist[:id]')", required=True, type=str)
                   ])
    def retrieve(self, request, *args, **kwargs):
        # --- Manual Role Check (Object Level) ---
        role_type, role_id = get_role_and_id_from_request(request)
        if not role_type:
             return Response({"error": "Role query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
             
        instance = self.get_object() # Raises 404 if not found
        
        allowed = False
        if role_type == 'cedars_specialist':
            allowed = True
        elif role_type == 'hku_member' and role_id:
            if str(instance.reservation.member.uid) == str(role_id):
                allowed = True
                
        if not allowed:
            return Response(
                {"error": "You do not have permission to access this rating."},
                status=status.HTTP_403_FORBIDDEN
            )
        # --- End Manual Role Check ---

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @extend_schema(exclude=True) # Standard POST is excluded, use custom action below
    def create(self, request, *args, **kwargs):
        return Response({"detail": "Method \"POST\" not allowed. Use /ratings/create/ instead."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @extend_schema(
        summary="Update rating (Specialists Only)",
        description="Update a rating. Only CEDARS specialists can perform this action. Uses manual role check.",
        parameters=[
            OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str)
        ]
    )
    def update(self, request, *args, **kwargs):
        # --- Manual Role Check ---
        role_type, _ = get_role_and_id_from_request(request)
        if role_type != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS Specialists can update ratings."},
                status=status.HTTP_403_FORBIDDEN
            )
        # --- End Manual Role Check ---
        
        # Standard update logic (from ModelViewSet)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been used, ensure the cache is cleared
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @extend_schema(
        summary="Partially update rating (Specialists Only)",
        description="Partially update a rating. Only CEDARS specialists can perform this action. Uses manual role check.",
        parameters=[
            OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str)
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        # --- Manual Role Check ---
        role_type, _ = get_role_and_id_from_request(request)
        if role_type != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS Specialists can update ratings."},
                status=status.HTTP_403_FORBIDDEN
            )
        # --- End Manual Role Check ---
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs) # Reuse the PUT logic

    @extend_schema(
        summary="Delete rating (Specialists Only)",
        description="Delete a rating. Only CEDARS specialists can delete ratings. Uses manual role check.",
        parameters=[
            OpenApiParameter(name="role", description="User role (must be 'cedars_specialist[:id]')", required=True, type=str)
        ]
    )
    def destroy(self, request, *args, **kwargs):
        role_type, _ = get_role_and_id_from_request(request)
        if role_type != 'cedars_specialist':
            return Response(
                {"error": "Only CEDARS Specialists can delete ratings."},
                status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    @extend_schema(
        summary="Create a new rating (HKU Members Only)",
        description="Rate an accommodation for a completed reservation. Only the HKU member associated with the reservation (matching UID in role) can create a rating. Uses manual role check.",
        request=RateAccommodationSerializer,
        parameters=[
            OpenApiParameter(
                name="role", 
                description="User role with ID (format: 'hku_member:uid')", 
                required=True,
                type=str
            )
        ],
        responses={
            201: RatingSerializer,
            400: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT
        }
    )
    @action(detail=False, methods=['post'], url_path='create',
            authentication_classes=[],
            permission_classes=[]) # Manual checks inside
    def create_rating(self, request):
        role_type, role_id = get_role_and_id_from_request(request)
        if role_type != 'hku_member' or not role_id:
            return Response(
                {"error": "Only HKU Members with a valid UID can create ratings.", "role_provided": request.query_params.get('role')},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        reservation_id = serializer.validated_data.get('reservation_id')
        try:
            reservation = Reservation.objects.select_related('member').get(
                pk=reservation_id, 
                member__uid=role_id 
            ) 
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found or does not belong to this user."}, status=status.HTTP_404_NOT_FOUND)
            
        today = datetime.now().date()
        if reservation.status in ['pending', 'confirmed'] and reservation.end_date < today:
            reservation.status = 'completed'
            reservation.save(update_fields=['status'])
        elif reservation.status != 'completed':
            return Response({"error": f"You can only rate completed reservations. Current status: {reservation.status}"}, status=status.HTTP_400_BAD_REQUEST)
            
        if Rating.objects.filter(reservation=reservation).exists():
            return Response(
                {"error": "A rating already exists for this reservation"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        score = serializer.validated_data.get('score')
        comment = serializer.validated_data.get('comment', '')
        
        rating = Rating.objects.create(
            score=score,
            comment=comment,
            date_rated=today,
            reservation=reservation
        )
        
        response_serializer = RatingSerializer(rating)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)