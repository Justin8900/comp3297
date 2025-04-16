"""
URL configuration for the UniHaven application.

This module defines the URL patterns for the REST API endpoints of the UniHaven application.
It uses Django REST Framework's DefaultRouter to automatically generate URL patterns
for the ViewSets defined in views.py.

The following endpoints are available:
- /property-owners/: CRUD operations for property owners
- /accommodations/: CRUD operations and search for accommodations
- /hku-members/: CRUD operations for HKU members
- /cedars-specialists/: CRUD operations for CEDARS specialists
- /reservations/: CRUD operations for reservations
- /ratings/: CRUD operations for ratings

Each endpoint supports standard REST operations:
- GET: List and retrieve
- POST: Create
- PUT/PATCH: Update
- DELETE: Remove
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Import from the views.py module directly
from .views import (
    PropertyOwnerViewSet, AccommodationViewSet, HKUMemberViewSet,
    CEDARSSpecialistViewSet, ReservationViewSet, RatingViewSet
)

# Use the router for full REST API functionality
router = DefaultRouter()
router.register(r'property-owners', PropertyOwnerViewSet, basename='property-owner')
router.register(r'accommodations', AccommodationViewSet, basename='accommodation')
router.register(r'hku-members', HKUMemberViewSet, basename='hku-member')
router.register(r'cedars-specialists', CEDARSSpecialistViewSet, basename='cedars-specialist')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'ratings', RatingViewSet, basename='rating')

urlpatterns = [
    path('', include(router.urls)),
] 