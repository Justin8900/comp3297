"""
URL configuration for the UniHaven application.

This module defines the URL patterns for the REST API endpoints of the UniHaven application.
It uses Django REST Framework's DefaultRouter to automatically generate URL patterns
for the ViewSets defined in views.py.

The following endpoints are available:
- /property-owners/: CRUD operations for property owners
- /accommodations/: CRUD operations and search for accommodations
  - /accommodations/search/: Advanced search for accommodations with filtering
  - /accommodations/{id}/reservations/: List reservations for a specific accommodation (CEDARS specialists only)
- /hku-members/: CRUD operations for HKU members
- /cedars-specialists/: CRUD operations for CEDARS specialists
  - /cedars-specialists/{id}/managed_accommodations/: List accommodations managed by a specialist
- /reservations/: CRUD operations for reservations
  - /reservations/create/: Create a new reservation
  - /reservations/{id}/cancel/: Cancel a reservation
- /ratings/: CRUD operations for ratings
  - /ratings/create/: Create a new rating for a reservation

Each endpoint supports standard REST operations:
- GET: List and retrieve
- POST: Create
- PUT/PATCH: Update
- DELETE: Remove

User roles are identified through the 'role' query parameter:
- cedars_specialist: CEDARS staff members
- hku_member: HKU students and staff
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Import from the views.py module directly
from .views import (
    PropertyOwnerViewSet, AccommodationViewSet, 
    MemberViewSet, SpecialistViewSet,
    ReservationViewSet, RatingViewSet
)

# Use the router for full REST API functionality
router = DefaultRouter()
router.register(r'property-owners', PropertyOwnerViewSet, basename='property-owner')
router.register(r'accommodations', AccommodationViewSet, basename='accommodation')
router.register(r'members', MemberViewSet, basename='member')
router.register(r'specialists', SpecialistViewSet, basename='specialist')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'ratings', RatingViewSet, basename='rating')

urlpatterns = [
    path('', include(router.urls)),
] 