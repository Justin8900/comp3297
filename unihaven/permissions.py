"""
Custom permissions for the UniHaven application.

This module defines custom permission classes to restrict access to views and actions
based on user roles (HKU Member, CEDARS Specialist, etc.).
"""

from rest_framework import permissions
from .models import Reservation, Rating, Accommodation # Import necessary models
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
        allowed_roles = ['cedars_specialist', 'ust_specialist', 'cu_specialist']
        if role_param.lower() in allowed_roles:
             return role_param.lower(), None
        else: # HKU members always require UID
             return None, None # Invalid format for non-specialist roles

def get_university_from_role(role_type):
    """Map role prefix to university code (e.g., 'ust_member' -> 'HKUST')."""
    if role_type in ['cedars_specialist', 'hku_specialist']:
        return 'hku'
    if role_type.startswith('hku'):
        return 'hku'
    elif role_type.startswith('ust'):
        return 'ust'
    elif role_type.startswith('cu'):
        return 'cu'
    return None

# --- Base Permissions ---
class BaseRolePermission(permissions.BasePermission):
    """
    Base class for permissions checking the 'role' query parameter.
    """
    message = 'Invalid role or insufficient permissions.' # Default message

    def get_role(self, request):
        return get_role_and_id_from_request(request)
    
    def get_university(self, role_type):
        return get_university_from_role(role_type)

# --- General Role Permissions --- 

class IsAnySpecialist(BaseRolePermission):
    """
    Allows access only if the role is '_specialist' (ID optional).
    Used for actions any specialist can perform without targeting a specific object.
    """
    message = 'This action requires a Specialist role.'
    def has_permission(self, request, view):
        role_type, _ = self.get_role(request)
        return role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']

class IsAnyMemberOrSpecialist(BaseRolePermission):
    """
    Allows access if the role is '_member:<uid>' or '_specialist[:id]'.
    Used for actions accessible to both roles (e.g., viewing accommodations).
    """
    message = 'This action requires a Member or Specialist role.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        return (
            (role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id) or
            role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']
        )
    #    if role_type == 'hku_member' and role_id:
    #        return True
    #    if role_type == 'cedars_specialist': # ID optional for specialist
    #        return True
    #    return False

# --- Specific Resource Permissions --- 

# Property Owners: Only CEDARS Specialists
# Use IsAnyCEDARSSpecialist for all actions.

# Accommodations:
# - List/Retrieve/Search: IsAnyHKUMemberOrCEDARSSpecialist
# - Create/Update/Delete: IsAnyCEDARSSpecialist
# - reservations action: IsAnyCEDARSSpecialist

# HKU Members:
class CanRetrieveUpdateMember(BaseRolePermission):
    """
    Allows CEDARS Specialists OR the specific HKU Member.
    """
    message = 'Only University Specialists or the specific Member can perform this action.'
    def has_permission(self, request, view):
        # Check if the role format is valid first
        role_type, role_id = self.get_role(request)
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
             return True
        if role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id:
             return True
        return False
        
    def has_object_permission(self, request, view, obj):
        role_type, role_id = self.get_role(request)
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
            return obj.university == self.get_university(role_type) 
        #if role_type == 'hku_member' and role_id:
             # obj is the HKUMember instance here
        return obj.uid == role_id
        #return False

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
    message = 'Requires University Specialist or Member role.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        # Allow CEDARS specialist (ID optional) or HKU member (ID required)
        return (
            role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist'] or
            (role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id)
        )

class CanCreateReservation(BaseRolePermission):
    """
    Allows HKU members (for self) or CEDARS specialists (for any specified member).
    """
    message = 'University Members can reserve for self; Specialists can reserve for any member.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
             # Specialist needs member_id in request data, checked in view
             return True
        if role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id:
             # Member must have UID
             return True
        return False

class CanAccessReservationObject(BaseRolePermission):
    """
    Object-level permission: Allows CEDARS Specialists OR the HKU Member owner.
    Used for Retrieve, Cancel.
    """
    message = 'Only University Specialists or the reservation owner can perform this action.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        # --- DEBUGGING PRINT --- 
        print(f"[DEBUG] CanAccessReservationObject: Checking has_permission for role_type='{role_type}', role_id='{role_id}'")
        # --- END DEBUGGING --- 
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
             return True
        if role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id:
             return True
        return False

    def has_object_permission(self, request, view, obj):
        role_type, role_id = self.get_role(request)
        # --- DEBUGGING PRINT --- 
        print(f"[DEBUG] CanAccessReservationObject: Checking object permission for role_type='{role_type}', role_id='{role_id}'")
        # --- END DEBUGGING --- 
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
             # --- DEBUGGING PRINT --- 
            print(f"[DEBUG] CanAccessReservationObject: Allowing CEDARS specialist.")
            # --- END DEBUGGING --- 
            return True # Specialists can access any reservation
        if role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id:
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
    message = 'Requires University Specialist or Member role.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        return role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist'] or (role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id)

class CanCreateRating(BaseRolePermission):
    """
    Allows only HKU members to create ratings for their own completed reservations.
    Further checks (completion, ownership) happen in the view.
    """
    message = 'Only University Members can create ratings.'
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        return role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id is not None

class CanAccessRatingObject(BaseRolePermission):
    """
    Object-level permission: Allows CEDARS Specialists OR the HKU Member owner of the rating's reservation.
    Used for Retrieve.
    """
    message = 'Only University Specialists or the rating owner can perform this action.'
    def has_permission(self, request, view):
        # Check if the role format is valid first
        role_type, role_id = self.get_role(request)
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
             return True
        if role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id:
             return True
        return False

    def has_object_permission(self, request, view, obj):
        role_type, role_id = self.get_role(request)
        request_uni = get_university_from_role(role_type)
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
            return True # Specialists can access any rating
        if role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id:
             # obj is the Rating instance here
             # Ensure the rating has a reservation and member linked correctly
            return hasattr(obj, 'reservation') and hasattr(obj.reservation, 'member') and obj.reservation.member.uid == role_id
        return False

class CanViewAccommodations(BaseRolePermission):
    """
    Allows access to university-specific accommodations or shared accommodations.
    """
    def has_permission(self, request, view):
        role_type, role_id = self.get_role(request)
        # Check if the role is a university member or specialist
        if role_type in ['hku_member', 'ust_member', 'cu_member'] and role_id:
            return True  # Members can view their university's accommodations
        
        # Allow specialists from all universities to view any shared accommodation
        if role_type in ['cedars_specialist', 'ust_specialist', 'cu_specialist']:
            return True
        
        return False

    def has_object_permission(self, request, view, obj):
        role_type, role_id = self.get_role(request)
        # Check if the accommodation is shared or belongs to the university
        if obj.is_shared:
            return True  # Any specialist or member can access shared accommodations
        return obj.university == self.get_university(role_type)  # Ensure the university matches

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