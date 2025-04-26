"""
Custom permissions for the UniHaven application.

This module defines custom permission classes to restrict access to views and actions
based on user roles (Member, Specialist) and their associated university.
Roles are expected in the format 'university_code:role_type:role_id' via the 'role' query parameter.
e.g., 'hku:member:1234567', 'cuhk:specialist:89'
"""

from rest_framework import permissions
from .models import Reservation, Rating, Accommodation, Member, Specialist, University # Use Member instead of BaseMember
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)

# Helper function to extract role info
def get_role_info_from_request(request):
    """
    Extract university code, role type, and role ID/UID from the 'role' query parameter.
    Expected format: 'university_code:role_type:role_id' 
                     or 'university_code:specialist' (ID optional for some specialist actions)
    Returns: tuple (university_code, role_type, role_id) or (None, None, None) if invalid/missing
    """
    role_param = request.query_params.get('role', '')
    if not role_param:
        return None, None, None # Role parameter is required

    parts = role_param.split(':')
    
    if len(parts) == 3:
        uni_code, role_type, role_id = parts
        # Basic validation: check if uni_code exists? Maybe too slow here.
        # Assume uni_code is valid for now.
        return uni_code.lower(), role_type.lower(), role_id
    elif len(parts) == 2:
        # Allow format 'uni_code:specialist' where ID might be optional
        uni_code, role_type = parts
        if role_type.lower() == 'specialist':
             return uni_code.lower(), role_type.lower(), None # Specialist ID is optional
        else: # Member role always requires an ID
             return None, None, None # Invalid format for member without ID
    else:
        return None, None, None # Invalid format

class BaseRolePermission(permissions.BasePermission):
    """
    Base class for permissions checking the 'role' query parameter using the new format.
    """
    message = 'Invalid role format, missing role, or insufficient permissions.' # Default message

    def get_role_info(self, request):
        """Gets role info using the helper function."""
        return get_role_info_from_request(request)

# --- General Role Permissions --- 

class IsSpecialist(BaseRolePermission):
    """
    Allows access only if the role is 'specialist' for any university.
    ID is optional. Used for actions any specialist can perform globally, 
    or where university context is checked later/in the view.
    """
    message = 'This action requires a Specialist role.'
    def has_permission(self, request, view):
        _, role_type, _ = self.get_role_info(request)
        return role_type == 'specialist'

class IsMember(BaseRolePermission):
    """
    Allows access only if the role is 'member' for any university.
    Requires Member ID (UID).
    """
    message = 'This action requires a Member role with a valid UID.'
    def has_permission(self, request, view):
        _, role_type, role_id = self.get_role_info(request)
        # Member role requires an ID (UID)
        return role_type == 'member' and role_id is not None

class IsMemberOrSpecialist(BaseRolePermission):
    """
    Allows access if the role is 'member' (with ID) or 'specialist' (ID optional).
    Used for actions accessible to both valid roles (e.g., viewing general accommodation lists).
    University-specific filtering often happens in the view based on the role info.
    """
    message = 'This action requires a Member or Specialist role.'
    def has_permission(self, request, view):
        uni_code, role_type, role_id = self.get_role_info(request)
        if not uni_code or not role_type:
            return False # Invalid role format
        
        if role_type == 'member' and role_id:
            return True
        if role_type == 'specialist': # ID optional for specialist
            return True
        return False

# --- Specific Resource Permissions --- 

# Property Owners: Actions likely restricted to Specialists.
# Use IsSpecialist for create/update/delete if PropertyOwner has its own endpoints.

# Accommodations:
# - List/Retrieve/Search: IsMemberOrSpecialist (View filters by uni for members)
# - Create/Update/Delete: Use IsSpecialistManagingAccommodation
# - reservations action: (Needs decision - IsSpecialist?)

class IsSpecialistManagingAccommodation(BaseRolePermission):
    """
    Object-level permission for managing Accommodation objects (Create, Update, Delete).
    Allows:
    - Specialists whose university is listed in the Accommodation's available_at_universities.
    
    For CREATE: Checks if the user is a specialist. The view/serializer should ensure
                the specialist's university is included in the initial available_at_universities list.
    For UPDATE/DELETE: Checks if the specialist's university is currently linked to the accommodation.
    """
    message = 'Only Specialists from a university associated with the accommodation can manage it.'

    def has_permission(self, request, view):
        # For list view (GET), this might be too restrictive if list is allowed for others.
        # But for Create (POST), we need to ensure it's a specialist making the request.
        uni_code, role_type, role_id = self.get_role_info(request)
        
        # Allow any Specialist to attempt Create/Update/Delete, object permission will verify.
        if role_type == 'specialist':
             # Further validation for Create (e.g., specialist's uni must be in request data)
             # should ideally happen in the serializer or view's perform_create.
             return True 
        
        # Deny if not a specialist role
        self.message = 'This action requires a Specialist role.'
        return False

    def has_object_permission(self, request, view, obj):
        # obj is the Accommodation instance (for Update/Delete/etc.)
        uni_code, role_type, role_id = self.get_role_info(request)

        # Basic check: Is the requestor a specialist?
        if role_type != 'specialist':
            self.message = "This action requires a Specialist role."
            return False

        # For update actions (PUT/PATCH), allow the attempt.
        # The detailed validation for adding universities happens in perform_update.
        if request.method in ['PUT', 'PATCH']:
            return True 

        # For other methods like DELETE, enforce that the specialist must be from 
        # a currently managing university.
        is_managing_university = obj.available_at_universities.filter(code__iexact=uni_code).exists()
        if not is_managing_university:
             self.message = f"Permission denied: Specialist from '{uni_code}' is not authorized to manage this accommodation."
             
        return is_managing_university

# Members (BaseMember subclasses like HKUMember, CUHKMember):
class CanAccessMemberObject(BaseRolePermission):
    """
    Object-level permission for Member objects.
    Allows:
    - Any Specialist.
    - The specific Member themselves.
    Checks if the requestor's university matches the object's university.
    """
    message = 'Only Specialists from the same university or the specific Member can perform this action.'
    
    def has_permission(self, request, view):
        # Basic check: Is the role valid format?
        uni_code, role_type, role_id = self.get_role_info(request)
        if not uni_code or not role_type:
             return False
        # Must be member (with ID) or specialist
        return (role_type == 'member' and role_id) or role_type == 'specialist'

    def has_object_permission(self, request, view, obj):
        # obj is the Member instance (e.g., HKUMember)
        uni_code, role_type, role_id = self.get_role_info(request)
        
        # --- Basic validation ---
        if not uni_code or not role_type:
            return False # Invalid role
        
        # --- University Check ---
        # The requesting role's university must match the member object's university
        if not hasattr(obj, 'university') or obj.university.code.lower() != uni_code:
             self.message = f"Permission denied: Action requires role from university '{obj.university.code}'."
             return False
             
        # --- Role Check ---
        if role_type == 'specialist':
            # Specialists from the member's university can access/modify
            return True 
        elif role_type == 'member' and role_id:
             # Member can access/modify their own profile
            is_self = obj.uid == role_id
            if not is_self:
                 self.message = "Members can only access their own profile."
            return is_self
            
        return False # Deny other roles or invalid formats

# Specialists: 
# Actions on Specialist model itself likely restricted to other specialists or superusers.
# Use IsSpecialist if Specialist has its own endpoints.

# Reservations:
class CanListCreateReservations(BaseRolePermission):
    """
    Permission for listing (filtered in view) and creating reservations.
    Allows:
    - Members (with ID) of any university.
    - Specialists of any university.
    Requires role info to be valid for view filtering/creation logic.
    """
    message = 'Requires a valid Member (with ID) or Specialist role.'
    def has_permission(self, request, view):
        uni_code, role_type, role_id = self.get_role_info(request)
        if not uni_code or not role_type:
             return False # Invalid role format
        
        # Members must have an ID to create/list their own
        if role_type == 'member' and role_id:
             return True
        # Specialists can list all/create for others (ID optional for listing, needed for creation target in view)
        if role_type == 'specialist':
             return True
        return False

class CanAccessReservationObject(BaseRolePermission):
    """
    Object-level permission to view/modify/delete Reservation objects.
    Allows:
    - Members to access their own reservations.
    - Specialists to access reservations within their university.
    - Denies DELETE for completed/cancelled reservations.
    """
    message = 'Cannot access reservations belonging to other users or universities.'

    def has_object_permission(self, request, view, obj):
        uni_code, role_type, role_id = self.get_role_info(request)
        if not uni_code:
            return False

        # Check if the object (reservation) belongs to the user or their university
        if role_type == 'member':
            if obj.member.uid != role_id:
                return False
        elif role_type == 'specialist':
            if obj.university.code.lower() != uni_code.lower():
                return False
        else:
            return False # Invalid role type

        # Additional check for DELETE actions: cannot cancel completed/cancelled
        if request.method == 'DELETE':
            if obj.status in ['completed', 'cancelled']:
                self.message = f'Cannot cancel reservations that are already {obj.status}.'
                return False
            
        return True

# Ratings:
class CanListRatings(BaseRolePermission):
    """
    Permission for listing ratings.
    Allows:
    - Members (with ID) of any university (filtered in view).
    - Specialists of any university (filtered in view).
    Requires role info to be valid for view filtering.
    """
    message = 'Requires a valid Member (with ID) or Specialist role to list ratings.'
    def has_permission(self, request, view):
        # Same logic as CanListCreateReservations
        uni_code, role_type, role_id = self.get_role_info(request)
        if not uni_code or not role_type:
             return False
        if role_type == 'member' and role_id:
             return True
        if role_type == 'specialist':
             return True
        return False

class CanCreateRating(BaseRolePermission):
    """
    Allows only Members (with ID) to create ratings.
    Further checks (reservation completion, ownership) happen in the view/serializer.
    Requires the member role to be from the correct university for the reservation.
    """
    message = 'Only Members can create ratings for their completed reservations.'
    def has_permission(self, request, view):
        # Check if the user has a valid Member role with ID
        uni_code, role_type, role_id = self.get_role_info(request)
        if not (uni_code and role_type == 'member' and role_id):
            return False
        
        # Additional check: Can this specific member create a rating for the reservation 
        # specified in the request body? This often needs to be checked in the view's perform_create
        # or the serializer's validate method, as we don't have the reservation object here.
        # We know they *are* a member, which is the basic requirement.
        return True 
        # Example check if reservation_id was in query params (not typical for POST):
        # reservation_id = request.query_params.get('reservation_id')
        # if reservation_id:
        #     try:
        #         res = Reservation.objects.get(id=reservation_id, member__uid=role_id, member__university__code=uni_code)
        #         return res.status == 'completed' 
        #     except Reservation.DoesNotExist:
        #         return False
        # return False # Deny if reservation_id not provided or doesn't match

class CanAccessRatingObject(BaseRolePermission):
    """
    Object-level permission for Rating objects (Retrieve).
    Allows:
    - Specialists from the rating's associated university.
    - The Member who owns the rating's reservation.
    """
    message = 'Only Specialists from the relevant university or the rating owner can perform this action.'
    
    def has_permission(self, request, view):
        # Basic role format check
        uni_code, role_type, role_id = self.get_role_info(request)
        if not uni_code or not role_type:
             return False
        return (role_type == 'member' and role_id) or role_type == 'specialist'

    def has_object_permission(self, request, view, obj):
        # obj is the Rating instance
        uni_code, role_type, role_id = self.get_role_info(request)
        
        # --- Basic validation ---
        if not uni_code or not role_type:
             return False # Invalid role

        # --- Ensure object has necessary attributes for checks ---
        if not hasattr(obj, 'reservation') or not obj.reservation \
           or not hasattr(obj.reservation, 'university') or not obj.reservation.university \
           or not hasattr(obj.reservation, 'member') or not obj.reservation.member:
            self.message = "Rating object is missing required reservation, university, or member information."
            return False

        # --- University Check ---
        # The requesting role's university must match the rating's reservation's university
        if obj.reservation.university.code.lower() != uni_code:
             self.message = f"Permission denied: Action requires role from university '{obj.reservation.university.code}'."
             return False

        # --- Role Check ---
        if role_type == 'specialist':
            # Specialists from the relevant university can access the rating
            return True
        elif role_type == 'member' and role_id:
            # Member can access ratings associated with their own reservations
            is_owner = obj.reservation.member.uid == role_id
            if not is_owner:
                 self.message = "Members can only access ratings for their own reservations."
            return is_owner

        return False # Deny other roles or invalid formats

class CanViewAccommodationDetail(BaseRolePermission):
    """
    Object-level permission to view Accommodation details.
    Allows:
    - Members if the accommodation is available at their university.
    - Specialists if the accommodation is available at their university.
    """
    message = 'Users can only view details of accommodations available at their university.'

    def has_object_permission(self, request, view, obj):
        logger.debug("--- Checking CanViewAccommodationDetail --- ") # Add logger
        uni_code, role_type, role_id = self.get_role_info(request)
        logger.debug(f"Role Info: uni_code={uni_code}, role_type={role_type}, role_id={role_id}")
        logger.debug(f"Object: Accommodation ID={obj.id}, Address={obj.address}")
        logger.debug(f"Object Universities: {[uni.code for uni in obj.available_at_universities.all()]}")
        
        if not uni_code: 
            logger.debug("Permission Denied: No uni_code in role.")
            return False

        # Check if the object (accommodation) is available at the user's university
        is_available = obj.available_at_universities.filter(code__iexact=uni_code).exists()
        logger.debug(f"Is available at {uni_code}? {is_available}")
        logger.debug("--- End Check --- ")
        return is_available

# Remove or comment out deprecated/unused classes if they exist
# --- DEPRECATED / UNUSED --- 
# class IsAnyCEDARSSpecialist ...
# class IsAnyHKUMemberOrCEDARSSpecialist ...
# class CanRetrieveUpdateHKUMember ...
# class CanListReservations ... (Replaced by CanListCreateReservations)
# class CanAccessReservationObject ... (Replaced by new version)
# class CanListRatings ... (Replaced by new version)
# class CanCreateRating ... (Replaced by new version)
# class CanAccessRatingObject ... (Replaced by new version) 