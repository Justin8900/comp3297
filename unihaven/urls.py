from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import search_accommodations

# router = DefaultRouter()
# router.register(r'property-owners', views.PropertyOwnerViewSet)
# router.register(r'accommodations', views.AccommodationViewSet)
# router.register(r'hku-members', views.HKUMemberViewSet)
# router.register(r'cedars-specialists', views.CEDARSSpecialistViewSet)

urlpatterns = [
    # path('', include(router.urls)),
    path('property-owners/', views.PropertyOwnerViewSet.as_view({'get': 'list'}), name='property_owner_list'),
    path('accommodations/', views.AccommodationViewSet.as_view({'get': 'list'}), name='accommodation_list'),
    path('search/', search_accommodations, name='search_accommodations'),
    path('accommodations/search/',search_accommodations, name='search_accommodations'),
] 