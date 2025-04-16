"""
Custom permissions for the UniHaven application.

This module defines custom permission classes to restrict access to views and actions
based on user roles (HKU Member, CEDARS Specialist, etc.).
"""

from rest_framework import permissions
from .models import Reservation, Rating, HKUMember, Accommodation # Import necessary models
from datetime import datetime

# Helper function to extract role and ID (moved here for reusability)
def get_role_and_id_from_request(request):
    """
    Extract role type and ID/UID from the 'role' query parameter.
    Returns: tuple (role_type, role_id) or (None, None) if invalid/missing
    """
    role_param = request.query_params.get('role', '')
    if not role_param:
        return None, None # Role is required
        
    if ':' in role_param:
        role_type, role_id = role_param.split(':', 1)
        return role_type.lower(), role_id
    else:
        # Allow role type without ID only if it's cedars_specialist for specific permissive actions
        if role_param.lower() == 'cedars_specialist':
             return role_param.lower(), None
        else: # HKU members always require UID
             return None, None # Invalid format for non-specialist roles

class BaseRolePermission(permissions.BasePermission):
    """
    Base class for permissions checking the 'role' query parameter.
    """
    message = 'Invalid role or insufficient permissions.' # Default message

    def get_role(self, request):
        return get_role_and_id_from_request(request)

# --- General Role Permissions --- 

class IsAnyCEDARSSpecialist(BaseRolePermission):
    """
    Allows access only if the role is 'cedars_specialist' (ID optional).
    Used for actions any specialist can perform without targeting a specific object.
    """
    message = 'This action requires a CEDARS Specialist role.'
    def has_permission(self, request, view):
        role_type, _ = self.get_role(request)
        return role_type == 'cedars_specialist'

class IsAnyHKUMemberOrCEDARSSpecialist(BaseRolePermission):
    """
    Allows access if the role is 'hku_member:<uid>' or 'cedars_specialist[:id]'.
    Used for actions accessible to both roles (e.g., viewing accommodations).
    """
    message = 'This action requires a HKU Member or CEDARS Specialist role.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        if role_type == 'hku_member' and role_id:
            return True
        if role_type == 'cedars_specialist': # ID optional for specialist
            return True
        return False

# --- Specific Resource Permissions --- 

# Property Owners: Only CEDARS Specialists
# Use IsAnyCEDARSSpecialist for all actions.

# Accommodations:
# - List/Retrieve/Search: IsAnyHKUMemberOrCEDARSSpecialist
# - Create/Update/Delete: IsAnyCEDARSSpecialist
# - reservations action: IsAnyCEDARSSpecialist

# HKU Members:
class CanRetrieveUpdateHKUMember(BaseRolePermission):
    """
    Allows CEDARS Specialists OR the specific HKU Member.
    """
    message = 'Only CEDARS Specialists or the specific HKU Member can perform this action.'
    def has_permission(self, request, view):
        # Check if the role format is valid first
        role_type, role_id = self.get_role(request)
        if role_type == 'cedars_specialist':
             return True
        if role_type == 'hku_member' and role_id:
             return True
        return False
        
    def has_object_permission(self, request, view, obj):
        role_type, role_id = self.get_role(request)
        if role_type == 'cedars_specialist':
            return True # Specialists can access any member
        if role_type == 'hku_member' and role_id:
             # obj is the HKUMember instance here
            return obj.uid == role_id
        return False

# CEDARS Specialists: Only CEDARS Specialists
# Use IsAnyCEDARSSpecialist for all actions.

# Reservations:
class CanListReservations(BaseRolePermission):
    """
    Allows CEDARS Specialists to list all, or HKU members to list their own (via member endpoint).
    NOTE: This permission is tricky for the main /reservations/ list endpoint.
    It's easier to handle the filtering logic within the view itself, 
    so we just check if the user is a valid role type here.
    The view will filter based on role_id if hku_member.
    """
    message = 'Requires CEDARS Specialist or HKU Member role.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        # Allow CEDARS specialist (ID optional) or HKU member (ID required)
        return role_type == 'cedars_specialist' or (role_type == 'hku_member' and role_id)

class CanCreateReservation(BaseRolePermission):
    """
    Allows HKU members (for self) or CEDARS specialists (for any specified member).
    """
    message = 'HKU Members can reserve for self; CEDARS Specialists can reserve for any member.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        if role_type == 'cedars_specialist':
             # Specialist needs member_id in request data, checked in view
             return True
        if role_type == 'hku_member' and role_id:
             # Member must have UID
             return True
        return False

class CanAccessReservationObject(BaseRolePermission):
    """
    Object-level permission: Allows CEDARS Specialists OR the HKU Member owner.
    Used for Retrieve, Cancel.
    """
    message = 'Only CEDARS Specialists or the reservation owner can perform this action.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        # --- DEBUGGING PRINT --- 
        print(f"[DEBUG] CanAccessReservationObject: Checking has_permission for role_type='{role_type}', role_id='{role_id}'")
        # --- END DEBUGGING --- 
        if role_type == 'cedars_specialist':
             return True
        if role_type == 'hku_member' and role_id:
             return True
        return False

    def has_object_permission(self, request, view, obj):
        role_type, role_id = self.get_role(request)
        # --- DEBUGGING PRINT --- 
        print(f"[DEBUG] CanAccessReservationObject: Checking object permission for role_type='{role_type}', role_id='{role_id}'")
        # --- END DEBUGGING --- 
        if role_type == 'cedars_specialist':
             # --- DEBUGGING PRINT --- 
            print(f"[DEBUG] CanAccessReservationObject: Allowing CEDARS specialist.")
            # --- END DEBUGGING --- 
            return True # Specialists can access any reservation
        if role_type == 'hku_member' and role_id:
             # obj is the Reservation instance here
             # Ensure the reservation has a member linked correctly
            allowed = hasattr(obj, 'member') and obj.member.uid == role_id
             # --- DEBUGGING PRINT --- 
            print(f"[DEBUG] CanAccessReservationObject: HKU member check - allowed={allowed}")
            # --- END DEBUGGING --- 
            return allowed
        # --- DEBUGGING PRINT --- 
        print(f"[DEBUG] CanAccessReservationObject: Denying by default.")
        # --- END DEBUGGING --- 
        return False

# Ratings:
class CanListRatings(BaseRolePermission):
    """
    Allows CEDARS Specialists to list all, or HKU members to list their own.
    Similar to CanListReservations, view handles filtering for HKU members.
    """
    message = 'Requires CEDARS Specialist or HKU Member role.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        return role_type == 'cedars_specialist' or (role_type == 'hku_member' and role_id)

class CanCreateRating(BaseRolePermission):
    """
    Allows only HKU members to create ratings for their own completed reservations.
    Further checks (completion, ownership) happen in the view.
    """
    message = 'Only HKU Members can create ratings.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        return role_type == 'hku_member' and role_id is not None

class CanAccessRatingObject(BaseRolePermission):
    """
    Object-level permission: Allows CEDARS Specialists OR the HKU Member owner of the rating's reservation.
    Used for Retrieve.
    """
    message = 'Only CEDARS Specialists or the rating owner can perform this action.'
    def has_permission(self, request, view):
        # Check if the role format is valid first
        role_type, role_id = self.get_role(request)
        if role_type == 'cedars_specialist':
             return True
        if role_type == 'hku_member' and role_id:
             return True
        return False

    def has_object_permission(self, request, view, obj):
        role_type, role_id = self.get_role(request)
        if role_type == 'cedars_specialist':
            return True # Specialists can access any rating
        if role_type == 'hku_member' and role_id:
             # obj is the Rating instance here
             # Ensure the rating has a reservation and member linked correctly
            return hasattr(obj, 'reservation') and hasattr(obj.reservation, 'member') and obj.reservation.member.uid == role_id
        return False

# --- DEPRECATED / UNUSED --- 
# Keeping original classes here for reference, but they are not used
# because they rely on request.user which is not how roles are passed.

# class IsHKUMember(permissions.BasePermission):
#     ...

# class IsCEDARSSpecialist(permissions.BasePermission):
#     ...

# class IsPropertyOwner(permissions.BasePermission):
#     ...

# class IsOwnerOrCEDARSSpecialist(permissions.BasePermission):
#     ... 