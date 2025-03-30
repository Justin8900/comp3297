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