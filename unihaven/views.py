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
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from .models import (
    University, PropertyOwner, Accommodation, Member, Specialist, 
    Reservation, Rating, UniversityLocation # Added UniversityLocation
)
from .serializers import (
    PropertyOwnerSerializer, AccommodationSerializer, 
    MemberSerializer, # Assuming a generic MemberSerializer exists/will be created
    SpecialistSerializer, # Assuming a generic SpecialistSerializer exists/will be created
    ReservationSerializer, RatingSerializer,
)
from .permissions import (
    IsSpecialist,
    IsMember,
    IsMemberOrSpecialist,
    IsSpecialistManagingAccommodation,
    CanAccessMemberObject,
    CanListCreateReservations,
    CanAccessReservationObject,
    CanListRatings,
    CanCreateRating,
    CanAccessRatingObject,
    CanViewAccommodationDetail,
    get_role_info_from_request # Updated helper function
)
from .utils.geocoding import geocode_address, calculate_distance
from .utils.notifications import send_reservation_notification, send_member_cancellation_notification
import math
import logging # Added for logging

logger = logging.getLogger(__name__) # Added logger

# Helper function to get role info and handle basic errors
def get_role_or_403(request):
    uni_code, role_type, role_id = get_role_info_from_request(request)
    if not uni_code or not role_type:
        raise PermissionDenied("Invalid or missing role information in query parameters.")
    # Optionally fetch University object here if needed frequently, handle ObjectDoesNotExist
    # try:
    #     university = University.objects.get(code__iexact=uni_code)
    # except University.DoesNotExist:
    #     raise PermissionDenied(f"University code '{uni_code}' not found.")
    return uni_code, role_type, role_id #, university

# API Views

# --- PropertyOwner ViewSet ---
@extend_schema_view(
    # Update descriptions and parameters to reflect new role format 'uni_code:specialist[:id]'
    list=extend_schema(
        summary="List property owners (Specialists Only)",
        description="List all property owners. Requires a Specialist role.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    create=extend_schema(
        summary="Create property owner (Specialists Only)",
        description="Create a new property owner. Requires a Specialist role.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    retrieve=extend_schema(
        summary="Retrieve property owner (Specialists Only)", 
        description="Retrieve details of a specific property owner. Requires a Specialist role.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    update=extend_schema(
        summary="Update property owner (Specialists Only)",
        description="Update a property owner. Requires a Specialist role.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    partial_update=extend_schema(
        summary="Partially update property owner (Specialists Only)",
        description="Partially update a property owner. Requires a Specialist role.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    destroy=extend_schema(
        summary="Delete property owner (Specialists Only)",
        description="Delete a property owner. Requires a Specialist role.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    )
)
class PropertyOwnerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing property owners. Requires Specialist role.
    """
    queryset = PropertyOwner.objects.all().order_by('id')
    serializer_class = PropertyOwnerSerializer
    # Use the new IsSpecialist permission
    permission_classes = [IsSpecialist] 

    # Standard methods can rely on permission_classes now, no need to override unless adding logic


# --- Accommodation ViewSet ---
@extend_schema_view(
    # Update descriptions and parameters for new role format 'uni_code:role_type:role_id'
    list=extend_schema(
        summary="List accommodations by university with filters",
        description="List accommodations available at the user's university, with optional filters for type, beds, bedrooms, price, availability dates, rating, and distance from a university location.",
        parameters=[
            OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str),
            OpenApiParameter(name="type", description="Filter by accommodation type (e.g., 'apartment', 'house', 'room')", required=False, type=str, enum=['apartment', 'house', 'room']),
            OpenApiParameter(name="min_beds", description="Minimum number of beds", required=False, type=int),
            OpenApiParameter(name="beds", description="Exact number of beds", required=False, type=int),
            OpenApiParameter(name="min_bedrooms", description="Minimum number of bedrooms", required=False, type=int),
            OpenApiParameter(name="bedrooms", description="Exact number of bedrooms", required=False, type=int),
            OpenApiParameter(name="max_price", description="Maximum daily price", required=False, type=float),
            OpenApiParameter(name="available_from", description="Available from date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="available_until", description="Available until date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="min_rating", description="Minimum average rating", required=False, type=float),
            OpenApiParameter(name="rating", description="Exact average rating (within 0.1)", required=False, type=float),
            OpenApiParameter(name="distance_from", description="Name of UniversityLocation to calculate distance from", required=False, type=str)
        ],
        responses={200: AccommodationSerializer(many=True)}
    ),
    create=extend_schema(
        summary="Create accommodation (Managing Specialists Only)",
        description="Create a new accommodation listing. Requires a Specialist role from a university intended to manage the accommodation.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    retrieve=extend_schema(
        summary="Retrieve an accommodation",
        description="Retrieve details for a specific accommodation if available at the user's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    update=extend_schema(
        summary="Update accommodation (Managing Specialists Only)",
        description="Update an accommodation listing. Requires a Specialist role from a university managing the accommodation.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    partial_update=extend_schema(
        summary="Partially update accommodation (Managing Specialists Only)",
        description="Partially update an accommodation listing. Requires a Specialist role from a university managing the accommodation.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    destroy=extend_schema(
        summary="Delete accommodation (Managing Specialists Only)",
        description="Delete an accommodation listing. Requires a Specialist role from a university managing the accommodation.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    nearby=extend_schema( # Schema for the new action
        summary="List accommodations sorted by distance",
        description="List accommodations available at the user's university, sorted by distance from a specified university location.",
        parameters=[
            OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str),
            OpenApiParameter(name="location_name", description="Name of the UniversityLocation to calculate distance from (e.g., 'Main Campus', 'CUHK Campus')", required=True, type=str)
        ],
        responses={200: AccommodationSerializer(many=True)}
    )
)
class AccommodationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing accommodations.
    Permissions vary by action. Filtering by university is applied.
    """
    queryset = Accommodation.objects.all().order_by('id') # Base queryset
    serializer_class = AccommodationSerializer
    # permission_classes = [IsMemberOrSpecialist] # Default - get_permissions overrides

    def list(self, request, *args, **kwargs):
        """List accommodations with filters for type, beds, bedrooms, price, dates, rating, and distance."""
        try:
            uni_code, role_type, role_id = get_role_or_403(request)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        queryset = self.get_queryset()

        # Apply type filter with validation
        if 'type' in request.query_params:
            type_value = request.query_params['type']
            valid_types = [choice[0] for choice in getattr(Accommodation, 'TYPE_CHOICES', [('apartment', 'Apartment'), ('house', 'House'), ('room', 'Room')])]
            if type_value not in valid_types:
                return Response({"error": f"Invalid type value. Must be one of: {', '.join(valid_types)}."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(type=type_value)
            
        # Apply other queryset filters
        if 'min_beds' in request.query_params:
            try:
                queryset = queryset.filter(beds__gte=int(request.query_params['min_beds']))
            except ValueError:
                return Response({"error": "Invalid min_beds value."}, status=status.HTTP_400_BAD_REQUEST)
            
        if 'beds' in request.query_params:
            try:
                queryset = queryset.filter(beds=int(request.query_params['beds']))
            except ValueError:
                return Response({"error": "Invalid beds value."}, status=status.HTTP_400_BAD_REQUEST)
            
        if 'min_bedrooms' in request.query_params:
            try:
                queryset = queryset.filter(bedrooms__gte=int(request.query_params['min_bedrooms']))
            except ValueError:
                return Response({"error": "Invalid min_bedrooms value."}, status=status.HTTP_400_BAD_REQUEST)
            
        if 'bedrooms' in request.query_params:
            try:
                queryset = queryset.filter(bedrooms=int(request.query_params['bedrooms']))
            except ValueError:
                return Response({"error": "Invalid bedrooms value."}, status=status.HTTP_400_BAD_REQUEST)
            
        if 'max_price' in request.query_params:
            try:
                queryset = queryset.filter(daily_price__lte=float(request.query_params['max_price']))
            except ValueError:
                return Response({"error": "Invalid max_price value."}, status=status.HTTP_400_BAD_REQUEST)
            
        today = datetime.now().date()
        
        if 'available_from' in request.query_params:
            try:
                available_from = datetime.strptime(request.query_params['available_from'], '%Y-%m-%d').date()
                queryset = queryset.filter(available_from__lte=available_from, available_until__gte=available_from)
            except ValueError:
                return Response({"error": "Invalid date format for available_from. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
                
        if 'available_until' in request.query_params:
            try:
                available_until = datetime.strptime(request.query_params['available_until'], '%Y-%m-%d').date()
                queryset = queryset.filter(available_from__lte=available_until, available_until__gte=available_until)
            except ValueError:
                return Response({"error": "Invalid date format for available_until. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        
        filtered_accommodations = queryset

        if 'min_rating' in request.query_params:
            try:
                min_rating = float(request.query_params['min_rating'])
                filtered_accommodations = [acc for acc in filtered_accommodations if acc.average_rating >= min_rating]
            except ValueError:
                return Response({"error": "Invalid min_rating value."}, status=status.HTTP_400_BAD_REQUEST)
            
        if 'rating' in request.query_params:
            try:
                rating = float(request.query_params['rating'])
                filtered_accommodations = [acc for acc in filtered_accommodations if abs(acc.average_rating - rating) < 0.1]
            except ValueError:
                return Response({"error": "Invalid rating value."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle distance-based filtering
        if 'distance_from' in request.query_params:
            location_name = request.query_params.get('distance_from', '')
            try:
                ref_location = UniversityLocation.objects.get(
                    university__code__iexact=uni_code, 
                    name__iexact=location_name
                )
                source_lat = ref_location.latitude
                source_lon = ref_location.longitude
            except UniversityLocation.DoesNotExist:
                return Response(
                    {"error": f"Location '{location_name}' not found for university '{uni_code}'."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.error(f"Error fetching UniversityLocation for list: {e}")
                return Response({"detail": "Error retrieving reference location."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            results = []
            for acc in filtered_accommodations:
                if acc.latitude is not None and acc.longitude is not None:
                    try:
                        distance = calculate_distance(source_lat, source_lon, acc.latitude, acc.longitude)
                        acc_data = AccommodationSerializer(acc, context=self.get_serializer_context()).data
                        acc_data['distance_km'] = round(distance, 2)
                        results.append(acc_data)
                    except Exception as e:
                        logger.error(f"Error calculating distance for accommodation {acc.id}: {e}")
                        continue
            results.sort(key=lambda x: x['distance_km'])
            return Response(results)
        
        # Serialize results without distance
        serializer = self.get_serializer(filtered_accommodations, many=True)
        return Response(serializer.data)

    def get_permissions(self):
        """Assign permissions based on action using new classes."""
        if self.action in ['list', 'nearby']: # Added 'nearby'
            # Both members and specialists can view, filtering happens in get_queryset
            permission_classes_list = [IsMemberOrSpecialist]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only specialists associated with the accommodation can modify
            permission_classes_list = [IsSpecialistManagingAccommodation]
        elif self.action == 'reservations': # Custom action for reservations on an accommodation
            # Decide who can see this - likely specialists managing it?
            permission_classes_list = [IsSpecialistManagingAccommodation]
        elif self.action == 'retrieve': # Add specific permission for retrieve
            # Base check first (is member or specialist)
            # Object check happens in retrieve method via check_object_permissions
            permission_classes_list = [IsMemberOrSpecialist, CanViewAccommodationDetail]
        else:
            # Default deny: Return empty list, DRF defaults usually deny if no perms grant access.
            permission_classes_list = []
            # permission_classes = [permissions.IsAdminUser] # Alternative: only allow admin
        return [permission() for permission in permission_classes_list]

    def get_queryset(self):
        """Filter accommodations based on the user's university for list/nearby actions."""
        queryset = super().get_queryset()
        # Only apply university filtering for list/nearby views
        if self.action in ['list', 'nearby']:
            try:
                uni_code, role_type, role_id = get_role_or_403(self.request)
                # Filter accommodations to show only those available at the user's university
                queryset = queryset.filter(available_at_universities__code__iexact=uni_code)
            except PermissionDenied:
                # If role is invalid/missing, return empty queryset for list actions
                queryset = queryset.none()
        # For retrieve, update, destroy, etc., return the base queryset.
        # get_object() will fetch the specific instance, and permissions handle access.
        return queryset.distinct() # Use distinct because of M2M filtering

    def retrieve(self, request, *args, **kwargs):
        """Retrieve an accommodation, explicitly checking object permissions."""
        instance = self.get_object()
        # Explicitly check object permissions after retrieving
        self.check_object_permissions(request, instance) 
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """Ensure creating specialist's university is included and handle geocoding."""
        try:
            uni_code, role_type, role_id = get_role_or_403(self.request)
        except PermissionDenied as e:
             raise serializers.ValidationError({"detail": str(e)}) from e

        # Ensure specialist role
        if role_type != 'specialist':
            raise PermissionDenied("Only Specialists can create accommodations.")
            
        # Get the specialist's university object
        try:
             specialist_university = University.objects.get(code__iexact=uni_code)
        except University.DoesNotExist:
             raise serializers.ValidationError(f"Specialist's university code '{uni_code}' not found.")

        # Validate that the specialist's university is in the M2M list being set
        # Serializer validation is a better place for this, but we check here too for safety.
        universities_data = serializer.validated_data.get('available_at_universities', [])
        university_pks = [uni.pk for uni in universities_data]

        if specialist_university.pk not in university_pks:
             raise serializers.ValidationError({
                 "available_at_universities": f"Specialist from {uni_code} cannot create accommodation without listing it under their own university."})

        # --- Option 1 Modification: Strict Creation Scope ---
        # Ensure available_at_universities ONLY contains the specialist's uni code during CREATE
        if len(universities_data) != 1 or universities_data[0].code.lower() != uni_code.lower():
            raise serializers.ValidationError({
                "available_at_universities": f"During creation, this field must contain only the creating specialist's university code ('{uni_code}')."
            })
        # --- End Modification ---

        # Save the instance first
        accommodation = serializer.save()

        # Handle geocoding after save
        if accommodation.address: # Or use structured address fields? update_geocoding needs check
            try:
                # Assuming update_geocoding now handles structured address or needs update
                accommodation.update_geocoding() 
            except Exception as e:
                logger.error(f"Geocoding failed for accommodation {accommodation.id}: {e}")
                # Decide if creation should fail or just log the error

    def perform_update(self, serializer):
        """Handle geocoding on update if address changes."""
        # logger.info(f"[Perform Update] Validated data received: {serializer.validated_data}") # Log validated data
        # Permissions checked by get_permissions and IsSpecialistManagingAccommodation
        address_changed = 'address' in serializer.validated_data # Or check specific fields
        
        # --- Validation moved to partial_update method --- 

        accommodation = serializer.save()

        # Re-geocode if address components changed
        if address_changed and accommodation.address: # Or check specific fields
             try:
                 accommodation.update_geocoding()
             except Exception as e:
                 logger.error(f"Geocoding failed during update for accommodation {accommodation.id}: {e}")

    def partial_update(self, request, *args, **kwargs):
        """Handle PATCH requests, validating university additions before proceeding."""
        # --- Option 1 Modification: Validate adding universities BEFORE serializer --- 
        if 'available_at_universities' in request.data:
            try:
                instance = self.get_object() # Get current object
                req_uni_code, req_role_type, req_role_id = get_role_or_403(request)
                
                if req_role_type == 'specialist':
                    current_uni_codes = set(u.code.lower() for u in instance.available_at_universities.all())
                    # Get requested codes directly from raw request data
                    requested_uni_codes_from_data = set(code.lower() for code in request.data.get('available_at_universities', []))
                    
                    # logger.info(f"[Acc {instance.id} PATCH] Checking Uni Add: Requester='{req_uni_code}', Current='{current_uni_codes}', Requested Raw='{requested_uni_codes_from_data}'")

                    for code_to_set in requested_uni_codes_from_data:
                        is_other_uni = code_to_set != req_uni_code.lower()
                        is_newly_added = code_to_set not in current_uni_codes
                        
                        # logger.info(f"[Acc {instance.id} PATCH] Checking code '{code_to_set}': is_other={is_other_uni}, is_new={is_newly_added}")

                        if is_newly_added and is_other_uni:
                            raise PermissionDenied(
                                f"Specialist from '{req_uni_code}' cannot add university '{code_to_set}'. You can only add your own university."
                            )
            except PermissionDenied as e:
                 # If check fails, return 403 immediately
                 return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
            except Exception as e:
                 logger.error(f"Error checking university additions during PATCH for Acc {instance.id}: {e}")
                 return Response({"detail": "An error occurred while processing university assignments."}, status=status.HTTP_400_BAD_REQUEST)
        # --- End Modification ---

        # If validation passes or wasn't needed, proceed with standard partial update
        return super().partial_update(request, *args, **kwargs)

    # update, partial_update, destroy rely on permissions and standard logic

    # Remove the old complex search action for now, focus on basic CRUD
    # If needed, it should be refactored to use get_role_or_403 and filter by uni_code
    # @action(...)
    # def search(self, request): ...

    # --- Custom Action: Nearby Accommodations ---
    @action(detail=False, methods=['get'], permission_classes=[IsMemberOrSpecialist], url_path='nearby')
    def nearby(self, request):
        """Returns accommodations sorted by distance from a specified university location."""
        try:
            uni_code, role_type, role_id = get_role_or_403(request)
        except PermissionDenied as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        location_name = request.query_params.get('location_name')
        if not location_name:
            return Response({"detail": "'location_name' query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the reference location coordinates
        try:
            ref_location = UniversityLocation.objects.get(
                university__code__iexact=uni_code, 
                name__iexact=location_name # Case-insensitive name matching
            )
            ref_lat = ref_location.latitude
            ref_lon = ref_location.longitude
        except UniversityLocation.DoesNotExist:
            return Response(
                {"detail": f"Location '{location_name}' not found for university '{uni_code}'."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e: # Catch other potential errors during lookup
            logger.error(f"Error fetching UniversityLocation: {e}")
            return Response({"detail": "Error retrieving reference location."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Get base queryset filtered by university availability
        queryset = self.get_queryset() 
        
        # Filter accommodations that have coordinates
        queryset = queryset.filter(latitude__isnull=False, longitude__isnull=False)

        # Calculate distances and store as a list of tuples (distance, accommodation_obj)
        accommodations_with_distance = []
        for acc in queryset:
            try:
                distance = calculate_distance(ref_lat, ref_lon, acc.latitude, acc.longitude)
                accommodations_with_distance.append((distance, acc))
            except Exception as e:
                 logger.error(f"Error calculating distance for accommodation {acc.id}: {e}")
                 # Optionally skip this accommodation or handle error differently
                 continue 

        # Sort by distance (the first element of the tuple)
        accommodations_with_distance.sort(key=lambda x: x[0])

        # Extract the sorted accommodation objects
        sorted_accommodations = [acc for dist, acc in accommodations_with_distance]

        # Use pagination if needed (standard pagination might not work directly with sorted list)
        # page = self.paginate_queryset(sorted_accommodations) # This might fail if not a QuerySet
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)
        
        # Serialize the sorted list without default pagination for now
        # Explicitly instantiate the serializer instead of self.get_serializer()
        serializer = AccommodationSerializer(sorted_accommodations, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


# --- Member ViewSet (Now uses concrete Member model) ---
@extend_schema_view(
    # Update descriptions and parameters for new role format and BaseMember
    list=extend_schema(
        summary="List members (Specialists Only)",
        description="List all members within the specialist's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    create=extend_schema(
        summary="Create member (Specialists Only)",
        description="Create a new member within the specialist's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    retrieve=extend_schema(
        summary="Retrieve a member by UID", 
        description="Retrieve a member by UID. Specialists can retrieve any member within their university. Members can only retrieve their own details.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    update=extend_schema(
        summary="Update a member by UID",
        description="Update a member by UID. Specialists can update any member within their university. Members can only update their own details.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    partial_update=extend_schema(
        summary="Partially update a member by UID",
        description="Partially update a member by UID. Specialists can update any member within their university. Members can only update their own details.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    destroy=extend_schema(
        summary="Delete member (Specialists Only)",
        description="Delete a member by UID within the specialist's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    )
)
class MemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing university members (using concrete Member model).
    Lookup field is UID. Permissions vary by action. Filtering by university.
    """
    queryset = Member.objects.all() 
    serializer_class = MemberSerializer 
    lookup_field = 'uid' 

    def get_permissions(self):
        """Assign permissions based on action."""
        if self.action in ['list', 'create', 'destroy']:
            permission_classes_list = [IsSpecialist]
        elif self.action in ['retrieve', 'update', 'partial_update', 'reservations']:
            # CanAccessMemberObject permission needs to check obj against concrete Member
            permission_classes_list = [CanAccessMemberObject] 
        else:
            # Replace DenyAll with empty list
            permission_classes_list = []
        return [permission() for permission in permission_classes_list]

    def get_queryset(self):
        """Filter members based on the specialist's university for list view."""
        queryset = super().get_queryset() # Start with Member.objects.all()
        # Only apply university filtering for the list action
        if self.action == 'list':
            try:
                uni_code, role_type, role_id = get_role_or_403(self.request)
                # List view is only for specialists (checked by get_permissions)
                if role_type == 'specialist':
                    # Specialists only see members of their own university
                    queryset = queryset.filter(university__code__iexact=uni_code).order_by('name')
                else:
                    # Non-specialists cannot list members
                    queryset = queryset.none()
            except PermissionDenied:
                queryset = queryset.none()
        # For retrieve, update, destroy, etc., return the base queryset.
        # get_object() will fetch the specific instance, and permissions handle access.
        return queryset

    def perform_create(self, serializer):
        """Ensure member is created under the specialist's university."""
        try:
            uni_code, role_type, role_id = get_role_or_403(self.request)
        except PermissionDenied as e:
            raise serializers.ValidationError({"detail": str(e)}) from e
            
        if role_type != 'specialist': 
             raise PermissionDenied("Only Specialists can create members.")

        try:
            university = University.objects.get(code__iexact=uni_code)
        except University.DoesNotExist:
            raise serializers.ValidationError(f"Specialist's university '{uni_code}' not found.")
        
        # Associate the member with the specialist's university
        serializer.save(university=university)

    # retrieve, update, partial_update, destroy rely on CanAccessMemberObject permission

    @extend_schema(
        summary="List reservations for a member",
        description="Get all reservations for a specific member (identified by UID in URL). Members can only view their own reservations. Specialists can view reservations for members within their university.",
        parameters=[
            OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str),
            OpenApiParameter(name="status", description="Filter reservations by status", required=False, type=str, enum=["pending", "confirmed", "cancelled", "completed"])
        ],
        responses={200: ReservationSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], permission_classes=[CanAccessMemberObject]) 
    def reservations(self, request, uid=None):
        member = self.get_object() # Fetches Member instance using uid lookup field
        queryset = Reservation.objects.filter(member=member).order_by('-created_at')
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        serializer = ReservationSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


# --- Specialist ViewSet (Generalized from CEDARSSpecialistViewSet) ---
@extend_schema_view(
    # Update descriptions and parameters
    list=extend_schema(
        summary="List specialists (Specialists Only)",
        description="List all specialists within the requesting specialist's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    create=extend_schema(
        summary="Create specialist (Admin/Superusers Only - TBD)",
        description="Create a new specialist. Typically restricted to superusers.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)],
        exclude=True # Exclude for now, requires higher privilege
    ),
    retrieve=extend_schema(
        summary="Retrieve specialist (Specialists Only)",
        description="Retrieve a specialist by ID within the same university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    update=extend_schema(
        summary="Update specialist (Admin/Superusers Only - TBD)",
        description="Update a specialist by ID. Typically restricted to superusers or self.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)],
         exclude=True # Exclude for now
    ),
    partial_update=extend_schema(
        summary="Partially update specialist (Admin/Superusers Only - TBD)",
        description="Partially update a specialist by ID. Typically restricted to superusers or self.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)],
         exclude=True # Exclude for now
    ),
    destroy=extend_schema(
        summary="Delete specialist (Admin/Superusers Only - TBD)",
        description="Delete a specialist by ID. Typically restricted to superusers.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)],
         exclude=True # Exclude for now
    )
)
# Rename CEDARSSpecialistViewSet -> SpecialistViewSet
class SpecialistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing university specialists.
    Permissions are restricted, especially for modification. Filtering by university.
    """
    queryset = Specialist.objects.all().order_by('university__code', 'name')
    serializer_class = SpecialistSerializer # Use generic SpecialistSerializer
    # Stricter permissions by default
    permission_classes = [IsSpecialist] # Base requirement

    def get_permissions(self):
        """Assign permissions - Restrict modifications for now."""
        if self.action in ['list', 'retrieve']:
            # Specialists can view others in their university
            permission_classes_list = [IsSpecialist] 
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Only allow Admins/Superusers for now - needs proper implementation
            permission_classes_list = [permissions.IsAdminUser] 
        else:
            # Replace DenyAll with empty list
            permission_classes_list = []
        return [permission() for permission in permission_classes_list]

    def get_queryset(self):
        """Filter specialists to show only those from the same university."""
        queryset = super().get_queryset()
        try:
            uni_code, role_type, role_id = get_role_or_403(self.request)
        except PermissionDenied:
             return queryset.none()
             
        if role_type == 'specialist':
            # Specialists only see others from their own university
            queryset = queryset.filter(university__code__iexact=uni_code)
        else: # Should not happen
             queryset = queryset.none()
             
        return queryset

    # Create, Update, Delete actions are restricted by get_permissions for now


# --- Reservation ViewSet ---
@extend_schema_view(
    # Update descriptions and parameters
    list=extend_schema(
        summary="List reservations (Members see own, Specialists see their Uni's)",
        description="List reservations based on role. Members see their own. Specialists see all reservations within their university.",
        parameters=[
            OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str),
            OpenApiParameter(name="member_id", description="Filter by member UID (Specialists only)", required=False, type=str),
            OpenApiParameter(name="accommodation_id", description="Filter by accommodation ID", required=False, type=int),
            OpenApiParameter(name="status", description="Filter by status", required=False, type=str, enum=["pending", "confirmed", "cancelled", "completed"])
        ]
    ),
    create=extend_schema( # Use standard create now with permissions
        summary="Create a new reservation",
        description="Create a new reservation. Members reserve for self. Specialists can reserve for members within their university (must provide member_id in request body).",
        request=ReservationSerializer, # Use standard serializer
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str)],
        responses={201: ReservationSerializer}
    ),
    retrieve=extend_schema(
        summary="Retrieve a reservation",
        description="Retrieve details of a specific reservation. Members can retrieve their own. Specialists can retrieve any reservation within their university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    update=extend_schema( # Allow PUT for specialists
        summary="Update reservation (Specialists Only)",
        description="Update a reservation (e.g., change status). Requires Specialist role from the reservation's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    partial_update=extend_schema( # Allow PATCH for specialists
        summary="Partially update reservation (Specialists Only)",
        description="Partially update a reservation. Requires Specialist role from the reservation's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    destroy=extend_schema( # Allow DELETE for specialists
        summary="Delete reservation (Specialists Only)",
        description="Delete a reservation. Requires Specialist role from the reservation's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    )
)
class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reservations. Permissions apply based on role and university.
    """
    queryset = Reservation.objects.all().order_by('-created_at')
    serializer_class = ReservationSerializer 

    def get_permissions(self):
        """Assign permissions based on action."""
        if self.action in ['list', 'create']:
            # Members (for self) or Specialists (for their uni)
            permission_classes_list = [CanListCreateReservations] 
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'cancel', 'confirm']: # Added custom actions
            # Member owner or Specialist from the reservation's uni
            permission_classes_list = [CanAccessReservationObject] 
        else:
            # Replace DenyAll with empty list
            permission_classes_list = []
        return [permission() for permission in permission_classes_list]

    def get_queryset(self):
        """Filter reservations based on role for LIST actions only."""
        queryset = super().get_queryset()

        # Only apply list filtering based on role
        if self.action == 'list':
            try:
                uni_code, role_type, role_id = get_role_or_403(self.request)
                if role_type == 'member':
                    queryset = queryset.filter(member__uid=role_id)
                elif role_type == 'specialist':
                    queryset = queryset.filter(university__code__iexact=uni_code)
                else:
                    # Invalid role type, return empty queryset
                    queryset = queryset.none()
                    
                # Apply query param filters if provided
                member_id_filter = self.request.query_params.get('member_id')
                accommodation_id_filter = self.request.query_params.get('accommodation_id')
                status_filter = self.request.query_params.get('status')

                if member_id_filter and role_type == 'specialist': # Only allow specialists to filter by member
                    queryset = queryset.filter(member__uid=member_id_filter)
                if accommodation_id_filter:
                    queryset = queryset.filter(accommodation__id=accommodation_id_filter)
                if status_filter:
                    queryset = queryset.filter(status=status_filter)

            except PermissionDenied:
                queryset = queryset.none()
        
        # For retrieve, update, partial_update, destroy, return unfiltered queryset.
        # Object-level permissions (CanAccessReservationObject) will handle access control.
        return queryset

    def perform_create(self, serializer):
        """Set reservation university and handle specialist creating for a member."""
        try:
            uni_code, role_type, role_id = get_role_or_403(self.request)
        except PermissionDenied as e:
            raise serializers.ValidationError({"detail": str(e)}) from e

        member_uid_to_reserve = None
        if role_type == 'member':
            member_uid_to_reserve = role_id # Member reserves for self
        elif role_type == 'specialist':
            member_uid_to_reserve = serializer.validated_data.get('member_id', None) 
            if not member_uid_to_reserve:
                 raise serializers.ValidationError("Specialists must provide 'member_id' in the request body to create a reservation.")
        else:
             raise PermissionDenied("Invalid role type for creating reservation.") # Should be caught by permissions

        # Find the member using the concrete Member model
        try:
             member = Member.objects.get(uid=member_uid_to_reserve, university__code__iexact=uni_code)
        except Member.DoesNotExist:
             raise serializers.ValidationError(f"Member with UID '{member_uid_to_reserve}' not found or does not belong to university '{uni_code}'.")

        # Get accommodation (serializer validation should ensure it exists)
        accommodation = serializer.validated_data['accommodation']
        
        # Validate accommodation availability at the member's university
        if not accommodation.available_at_universities.filter(pk=member.university.pk).exists():
             raise serializers.ValidationError(f"Accommodation {accommodation.id} is not available at university {member.university.code}.")

        # Check for overlapping reservations (basic check, might need more robust logic)
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        overlaps = Reservation.objects.filter(
            accommodation=accommodation,
            status__in=['pending', 'confirmed'],
            start_date__lt=end_date,
            end_date__gt=start_date
        ).exists()
        if overlaps:
             raise serializers.ValidationError("Accommodation is not available for the selected dates due to an overlapping reservation.")

        # Save with the correct member and university
        # The model's save method should handle setting university from member if needed
        serializer.save(member=member, university=member.university) 
        # post_save signal in models.py handles notification

        # --- Send Notification for New Reservation ---
        instance = serializer.instance # Get the created instance
        subject = f"New Pending Reservation at {instance.university.code}: #{instance.id}"
        message_template = f"""
A new reservation requires confirmation:

Reservation ID: {{id}}
Member: {{member_name}} ({{member_uid}})
Accommodation: {{accommodation}}
Check-in: {{start_date}}
Check-out: {{end_date}}
Status: {{status}}

Please review and confirm or cancel this reservation.

Regards,
The UniHaven Team
        """
        send_reservation_notification(instance, subject, message_template)
        # --- End Notification --- 

    def perform_destroy(self, instance):
        """Handle notifications before deleting/cancelling."""
        try:
            uni_code, role_type, role_id = get_role_or_403(self.request)
            cancelling_user_type = role_type # member or specialist
        except PermissionDenied:
            cancelling_user_type = 'system' # Or handle error appropriately
        
        logger.info(f"Performing destroy for Reservation {instance.id}, cancelled by {cancelling_user_type}")

        # --- Send Notifications Before Deletion --- 
        subject_spec = f"Reservation Cancelled at {instance.university.code}: #{instance.id}"
        message_spec = f"""
The following reservation has been cancelled:

Reservation ID: {{id}}
Accommodation: {{accommodation}}
Member: {{member_name}} ({{member_uid}})
Cancelled by: {cancelling_user_type} # Use role type from request

Regards,
The UniHaven Team
        """
        # Notify relevant specialists
        send_reservation_notification(instance, subject_spec, message_spec)

        # Notify member if cancelled by specialist/system
        if cancelling_user_type != 'member':
             # We need the full Member object to get email, instance.member should work
             if hasattr(instance, 'member') and instance.member:
                 send_member_cancellation_notification(instance)
             else:
                 logger.warning(f"Cannot send member cancellation email for Res {instance.id} - member data missing.")
        # --- End Notifications --- 

        # Now, proceed with the actual deletion/cancellation
        # Option 1: Just delete (if that's the intended behaviour of DELETE)
        # instance.delete() 
        
        # Option 2: Use the model's cancel method (sets status to cancelled)
        instance.cancel(user_type=cancelling_user_type)

    # Add other methods like perform_update if needed, applying permissions



# --- Rating ViewSet ---
@extend_schema_view(
    # Update descriptions and parameters
    list=extend_schema(
        summary="List ratings (Members see own, Specialists see their Uni's)",
        description="List ratings based on role. Members see ratings for their reservations. Specialists see all ratings within their university.",
        parameters=[
            OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str),
            OpenApiParameter(name="reservation_id", description="Filter by reservation ID", required=False, type=int),
            OpenApiParameter(name="accommodation_id", description="Filter by accommodation ID", required=False, type=int),
            OpenApiParameter(name="member_id", description="Filter by member UID (Specialists only)", required=False, type=str)
        ]
    ),
     create=extend_schema( # Use standard create with permissions
        summary="Create a new rating (Members Only)",
        description="Rate an accommodation for a completed reservation. Only the Member associated with the reservation can create a rating.",
        request=RatingSerializer, # Use standard serializer
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid')", required=True, type=str)],
        responses={201: RatingSerializer}
    ),
    retrieve=extend_schema(
        summary="Retrieve a rating",
        description="Retrieve details of a specific rating. Members can retrieve ratings for their own reservations. Specialists can retrieve any rating within their university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:member:uid' or 'uni_code:specialist[:id]')", required=True, type=str)]
    ),
    update=extend_schema( # Allow update for specialists? Or disallow edits? Let's restrict for now.
        summary="Update rating (Admin/Superusers Only - TBD)",
        description="Update a rating. Typically restricted.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)],
        exclude=True
    ),
    partial_update=extend_schema( # Allow partial update for specialists? Or disallow edits? Let's restrict for now.
        summary="Partially update rating (Admin/Superusers Only - TBD)",
        description="Partially update a rating. Typically restricted.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)],
        exclude=True
    ),
    destroy=extend_schema( # Allow specialists to delete ratings?
        summary="Delete rating (Specialists Only)",
        description="Delete a rating. Requires Specialist role from the rating's university.",
        parameters=[OpenApiParameter(name="role", description="User role (format: 'uni_code:specialist[:id]')", required=True, type=str)]
    )
)
class RatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ratings. Permissions apply based on role and university.
    Rating creation restricted to members for their completed reservations.
    """
    queryset = Rating.objects.all().order_by('-date_rated')
    serializer_class = RatingSerializer

    def get_permissions(self):
        """Assign permissions based on action."""
        if self.action == 'list':
            permission_classes_list = [CanListRatings]
        elif self.action == 'create':
             # Only members can create, additional checks in perform_create/serializer
            permission_classes_list = [CanCreateRating] 
        elif self.action == 'retrieve':
            # Member owner or Specialist from the rating's uni
            permission_classes_list = [CanAccessRatingObject]
        elif self.action == 'destroy':
             # Allow specialists from the rating's uni to delete
             permission_classes_list = [CanAccessRatingObject] # Re-use, but need role check inside? No, checks uni match
             # Add check inside destroy if needed: if role != specialist: raise PermissionDenied
        elif self.action in ['update', 'partial_update']:
             # Disallow updates for now, or use IsAdminUser
             permission_classes_list = [permissions.IsAdminUser] # Example: restrict updates
        else:
            # Replace DenyAll with empty list
            permission_classes_list = []
        return [permission() for permission in permission_classes_list]

    def get_queryset(self):
        """Filter ratings based on the user's role and university."""
        queryset = super().get_queryset()
        try:
            uni_code, role_type, role_id = get_role_or_403(self.request)
        except PermissionDenied:
             return queryset.none()

        if role_type == 'member':
            # Members only see ratings for their own reservations
            queryset = queryset.filter(reservation__member__uid=role_id, reservation__university__code__iexact=uni_code)
        elif role_type == 'specialist':
            # Specialists see all ratings for their university
            queryset = queryset.filter(reservation__university__code__iexact=uni_code)
            # Optional filtering for specialists
            member_filter = self.request.query_params.get('member_id')
            accommodation_filter = self.request.query_params.get('accommodation_id')
            reservation_filter = self.request.query_params.get('reservation_id')
            if member_filter:
                 queryset = queryset.filter(reservation__member__uid=member_filter)
            if accommodation_filter:
                 queryset = queryset.filter(reservation__accommodation_id=accommodation_filter)
            if reservation_filter:
                 queryset = queryset.filter(reservation_id=reservation_filter)
        else:
            queryset = queryset.none()

        # queryset = queryset.select_related('reservation', 'reservation__member', 'reservation__accommodation', 'reservation__university')
        return queryset

    def perform_create(self, serializer):
        """Ensure the rating is created by the correct member for their completed reservation."""
        try:
            uni_code, role_type, role_id = get_role_or_403(self.request)
        except PermissionDenied as e:
            raise serializers.ValidationError({"detail": str(e)}) from e
            
        if role_type != 'member': # Should be caught by permission class
             raise PermissionDenied("Only Members can create ratings.")

        # Get reservation from serializer (validated to exist)
        reservation = serializer.validated_data['reservation']

        # 1. Check Ownership: Does the reservation belong to the member making the request?
        if reservation.member.uid != role_id:
             raise serializers.ValidationError("You can only rate your own reservations.")
             
        # 2. Check University Match (belt-and-suspenders check)
        if reservation.university.code.lower() != uni_code.lower():
             raise serializers.ValidationError("Cannot rate a reservation from a different university.")

        # 3. Check Status: Is the reservation completed?
        if reservation.status != 'completed':
            raise serializers.ValidationError("You can only rate completed reservations.")

        # 4. Check if Already Rated (OneToOneField should handle this at DB level, but check anyway)
        if hasattr(reservation, 'rating'):
             raise serializers.ValidationError("This reservation has already been rated.")

        # Save the rating (implicitly linked to reservation's member and uni)
        serializer.save() # Don't need to pass user/uni, it's inferred from reservation

    def perform_destroy(self, instance):
         """Ensure only specialists are deleting ratings."""
         try:
             uni_code, role_type, role_id = get_role_or_403(self.request)
             if role_type != 'specialist':
                 # This should be caught by get_permissions ideally, but double-check
                 raise PermissionDenied("Only specialists can delete ratings.") 
         except PermissionDenied as e:
             # Re-raise to prevent deletion
             raise e
         
         # If specialist check passes (and CanAccessRatingObject check passed), proceed
         super().perform_destroy(instance)


# --- Remove old manual actions if they are now handled by standard methods ---
# e.g., create_reservation, cancel, create_rating might be removable if standard
# create/destroy/custom actions cover them with new permissions.
# Review ReservationViewSet actions:
# - create_reservation -> Replaced by standard create + perform_create logic
# - cancel -> Refactored using custom action and CanAccessReservationObject
# Review RatingViewSet actions:
# - create_rating -> Replaced by standard create + perform_create logic


# --- HTML Views (Keep or Remove?) ---
# These might need updating or removal depending on project scope

class AccommodationListView(ListView):
    model = Accommodation
    template_name = 'unihaven/accommodation_list.html' 
    context_object_name = 'accommodations'

    def get_queryset(self):
        # Basic example, needs role/university filtering based on session/other auth
        return Accommodation.objects.order_by('?')[:10] # Random 10 for example

# Render basic search page
@api_view(['GET'])
@renderer_classes([TemplateHTMLRenderer, JSONRenderer])
@permission_classes([permissions.AllowAny]) # Or use appropriate role check
def accommodation_search_view(request):
    # This likely needs role checking and context passing for a real app
    context = {'some_key': 'some_value'} 
    # If HTML requested, render template
    if request.accepted_renderer.format == 'html':
        return Response(context, template_name='unihaven/accommodation_search.html')
    # Otherwise, maybe return search options as JSON?
    return Response({"message": "Use the API endpoint /accommodations/search/ for JSON search."})