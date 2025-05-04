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