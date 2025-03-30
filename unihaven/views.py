from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q
from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from datetime import datetime
from .models import *
from .serializers import *
from .utils.geocoding import geocode_address

# Create your views here.

# API Views
class PropertyOwnerViewSet(viewsets.ModelViewSet):
    queryset = PropertyOwner.objects.all()
    serializer_class = PropertyOwnerSerializer

class AccommodationViewSet(viewsets.ModelViewSet):
    queryset = Accommodation.objects.all().select_related('owner')
    serializer_class = AccommodationSerializer
    filter_backends = [filters.OrderingFilter]
    # filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['address', 'geo_address', 'type']
    ordering_fields = ['daily_price', 'rating', 'beds', 'bedrooms', 'available_from', 'available_until']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Apply filters based on query parameters
        if 'type' in self.request.query_params:
            queryset = queryset.filter(type=self.request.query_params['type'])
        
        if 'owner_id' in self.request.query_params:
            queryset = queryset.filter(owner_id=self.request.query_params['owner_id'])
        
        if 'available_now' in self.request.query_params and self.request.query_params['available_now'].lower() == 'true':
            today = datetime.now().date()
            queryset = queryset.filter(available_from__lte=today, available_until__gte=today)
        
        if 'min_price' in self.request.query_params:
            queryset = queryset.filter(daily_price__gte=self.request.query_params['min_price'])
        
        if 'max_price' in self.request.query_params:
            queryset = queryset.filter(daily_price__lte=self.request.query_params['max_price'])
        
        if 'min_rating' in self.request.query_params:
            queryset = queryset.filter(rating__gte=self.request.query_params['min_rating'])
        
        if 'min_beds' in self.request.query_params:
            queryset = queryset.filter(beds__gte=self.request.query_params['min_beds'])
        
        if 'address_contains' in self.request.query_params:
            search_term = self.request.query_params['address_contains']
            queryset = queryset.filter(
                Q(address__icontains=search_term) | 
                Q(geo_address__icontains=search_term)
            )
            
        return queryset
    
    def perform_create(self, serializer):
        # First save the accommodation with the provided data
        accommodation = serializer.save()
        
        # Then attempt to geocode the address
        if accommodation.address:
            lat, lng, geo = geocode_address(accommodation.address)
            if lat is not None and lng is not None and geo is not None:
                accommodation.latitude = lat
                accommodation.longitude = lng
                accommodation.geo_address = geo
                accommodation.save()
                
        return accommodation
        
    def perform_update(self, serializer):
        # Check if address has changed
        if serializer.instance.address != serializer.validated_data.get('address', serializer.instance.address):
            # Save first to update the address
            accommodation = serializer.save()
            
            # Then geocode the new address
            lat, lng, geo = geocode_address(accommodation.address)
            if lat is not None and lng is not None and geo is not None:
                accommodation.latitude = lat
                accommodation.longitude = lng
                accommodation.geo_address = geo
                accommodation.save()
        else:
            # No address change, just save normally
            accommodation = serializer.save()
            
        return accommodation

class HKUMemberViewSet(viewsets.ModelViewSet):
    queryset = HKUMember.objects.all()
    serializer_class = HKUMemberSerializer

class CEDARSSpecialistViewSet(viewsets.ModelViewSet):
    queryset = CEDARSSpecialist.objects.all()
    serializer_class = CEDARSSpecialistSerializer

