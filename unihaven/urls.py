"""
URL configuration for the UniHaven application.

This module defines the URL patterns for the REST API endpoints of the UniHaven application.
It uses Django REST Framework's DefaultRouter to automatically generate URL patterns
for the ViewSets defined in views.py.

The following endpoints are available:
- /api/property-owners/: CRUD operations for property owners
- /api/accommodations/: CRUD operations and search for accommodations
- /api/hku-members/: CRUD operations for HKU members
- /api/cedars-specialists/: CRUD operations for CEDARS specialists

Each endpoint supports standard REST operations:
- GET: List and retrieve
- POST: Create
- PUT/PATCH: Update
- DELETE: Remove
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Use the router for full REST API functionality
router = DefaultRouter()
router.register(r'property-owners', views.PropertyOwnerViewSet)
router.register(r'accommodations', views.AccommodationViewSet)
router.register(r'hku-members', views.HKUMemberViewSet)
router.register(r'cedars-specialists', views.CEDARSSpecialistViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 