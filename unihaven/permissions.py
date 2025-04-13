"""
Custom permissions for the UniHaven application.

This module defines custom permission classes to restrict access to views and actions
based on user roles (HKU Member, CEDARS Specialist, etc.).
"""

from rest_framework import permissions

class IsHKUMember(permissions.BasePermission):
    """
    Permission to only allow HKU members to access their own resources.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user is authenticated and is a HKU member.
        """
        return request.user.is_authenticated and hasattr(request.user, 'hkumember')
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the HKU member is accessing their own resources.
        
        For reservations, check if the reservation belongs to the member.
        For other objects, defer to the view for more specific checks.
        """
        if not request.user.is_authenticated or not hasattr(request.user, 'hkumember'):
            return False
            
        # If this is a reservation, check that it belongs to this member
        if hasattr(obj, 'member'):
            return obj.member.uid == request.user.hkumember.uid
            
        # If it's the member themselves, check that it's the same member
        if hasattr(obj, 'uid'):
            return obj.uid == request.user.hkumember.uid
            
        return False

class IsCEDARSSpecialist(permissions.BasePermission):
    """
    Permission to only allow CEDARS specialists to perform certain actions.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user is authenticated and is a CEDARS specialist.
        """
        return request.user.is_authenticated and hasattr(request.user, 'cedarsspecialist')
    
    def has_object_permission(self, request, view, obj):
        """
        CEDARS specialists have access to all objects for now.
        More specific checks can be added in the future.
        """
        return request.user.is_authenticated and hasattr(request.user, 'cedarsspecialist')

class IsPropertyOwner(permissions.BasePermission):
    """
    Permission to only allow property owners to access their own properties.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user is authenticated and is a property owner.
        """
        return request.user.is_authenticated and hasattr(request.user, 'propertyowner')
    
    def has_object_permission(self, request, view, obj):
        """
        Check if the property owner is accessing their own properties.
        """
        if not request.user.is_authenticated or not hasattr(request.user, 'propertyowner'):
            return False
            
        # If this is an accommodation, check that it belongs to this owner
        if hasattr(obj, 'owner'):
            return obj.owner.id == request.user.propertyowner.id
            
        # If it's the owner themselves, check that it's the same owner
        if hasattr(obj, 'id') and hasattr(obj, 'name') and not hasattr(obj, 'owner'):
            return obj.id == request.user.propertyowner.id
            
        return False

class IsOwnerOrCEDARSSpecialist(permissions.BasePermission):
    """
    Permission to allow both property owners and CEDARS specialists access.
    
    Property owners can only access their own properties.
    CEDARS specialists can access any property.
    """
    
    def has_permission(self, request, view):
        """
        Check if the user is authenticated and is either a property owner or a CEDARS specialist.
        """
        return (request.user.is_authenticated and 
                (hasattr(request.user, 'propertyowner') or 
                 hasattr(request.user, 'cedarsspecialist')))
    
    def has_object_permission(self, request, view, obj):
        """
        Property owners can only access their own properties.
        CEDARS specialists can access any property.
        """
        if not request.user.is_authenticated:
            return False
            
        # CEDARS specialists can access any accommodation
        if hasattr(request.user, 'cedarsspecialist'):
            return True
            
        # Property owners can only access their own accommodations
        if hasattr(request.user, 'propertyowner') and hasattr(obj, 'owner'):
            return obj.owner.id == request.user.propertyowner.id
            
        return False 