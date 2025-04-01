from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q
from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from datetime import datetime
from .models import *
from .serializers import *
from .utils.geocoding import geocode_address
import math
# Create your views here.

# API Views
class PropertyOwnerViewSet(viewsets.ModelViewSet):
    queryset = PropertyOwner.objects.all()
    serializer_class = PropertyOwnerSerializer

class AccommodationViewSet(viewsets.ModelViewSet):
    queryset = Accommodation.objects.all().select_related('owner')
    serializer_class = AccommodationSerializer
    filter_backends = [filters.OrderingFilter]
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
    
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        print("Search function reached")   
        query = Accommodation.objects.all()
        accommodation_type = request.GET.get('type')
        min_beds = request.GET.get('min_beds')
        exact_beds = request.GET.get('beds')
        min_bedrooms = request.GET.get('min_bedrooms')
        exact_bedrpooms = request.GET.get('bedrooms')
        min_rating = request.GET.get('min_rating')
        exact_rating = request.GET.get('rating')
        max_price = request.GET.get('max_price')
        available_from = request.GET.get('available_from')
        available_until = request.GET.get('available_until')
        distance_from = request.GET.get('distance_from')  # Building name
        selected = {
        "Main Campus": (22.28405, 114.13784),
        "Sassoon Road Campus": (22.2675, 114.12881),
        "Swire Institute of Marine Science": (22.20805, 114.26021),
        "Kadoorie Centre": (22.43022, 114.11429),
        "Faculty of Dentistry": (22.28649, 114.14426),}
        R = 6371 

        if accommodation_type:
            query = query.filter(type=accommodation_type)
        
        if min_beds:
            query = query.filter(beds__gte=int(min_beds))#>=
        
        if exact_beds: #exact beds
            query = query.filter(beds=int(exact_beds)) 
        
        if min_bedrooms:
            query = query.filter(bedrooms__gte= int(min_bedrooms)) #>=
        
        if exact_bedrpooms: #exact bedrooms
            query = query.filter(bedrooms=int(exact_bedrpooms)) #exact bedrooms
        
        if available_from:
            query = query.filter(available_from__gte=datetime.strptime(available_from, "%Y-%m-%d")) #>=

        if available_until:
                query = query.filter(available_until__lte=datetime.strptime(available_until, "%Y-%m-%d")) #<=

        if min_rating:
            query = query.filter(rating__gte=int(min_rating)) #>=

        if exact_rating: #exact rating
            query = query.filter(rating=int(exact_rating))
    
        if max_price:
            query = query.filter(daily_price__lte=Decimal(max_price)) #<=

        if distance_from:
            if distance_from in selected:
                ref_lat, ref_lon = selected[distance_from]
            else:
                ref_lat, ref_lon, _ = geocode_address(distance_from)
            if ref_lat is not None and ref_lon is not None:
                accommodations_with_distance = []
                for accommodation in query:
                    if accommodation.latitude is None or accommodation.longitude is None:
                        continue  

                    lat1, lon1 = math.radians(ref_lat), math.radians(ref_lon)
                    lat2, lon2 = math.radians(accommodation.latitude), math.radians(accommodation.longitude)
                    x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
                    y = (lat2 - lat1)
                    d = math.sqrt(x*x + y*y) * R 
                    accommodations_with_distance.append((d, accommodation))

                accommodations_with_distance.sort(key=lambda item: item[0])
                results = []
                for d, acc in accommodations_with_distance:
                    results.append({
                        'id': acc.id,
                        'type': acc.type,
                        'address': acc.address,
                        'beds': acc.beds,
                        'bedrooms': acc.bedrooms,
                        'rating': acc.rating,
                        'daily_price': acc.daily_price,
                        'available_from': acc.available_from,
                        'available_until': acc.available_until,
                        'distance_km': round(d, 2),
                    })
            else:
                results = {"error": "Invalid location specified"}
        else:
            results =list(query.values('id', 'type', 'address', 'beds', 'bedrooms', 'rating', 'daily_price', 'available_from', 'available_until'))
        
        return Response(results)
    
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

# @api_view(['GET'])
# def search_accommodations(request):
#     """
#     Search for accommodations based on query parameters.
#     """
#     print("Search function reached")   
#     query = Accommodation.objects.all()
   
#     accommodation_type = request.GET.get('type')
#     min_beds = request.GET.get('min_beds')
#     min_bedrooms = request.GET.get('min_bedrooms')
#     min_rating = request.GET.get('min_rating')
#     max_price = request.GET.get('max_price')
#     available_from = request.GET.get('available_from')
#     available_until = request.GET.get('available_until')
#     distance_from = request.GET.get('distance_from')  # Building name
    
#     # Apply filters if parameters are provided
#     if accommodation_type:
#         query = query.filter(type=accommodation_type)
    
#     if min_beds:
#         query = query.filter(beds__gte=int(min_beds))
    
#     if min_bedrooms:
#         query = query.filter(bedrooms__gte= int(min_bedrooms))
    
#     if available_from:
#         query = query.filter(available_from__gte=datetime.strptime(available_from, "%Y-%m-%d"))

#     if available_until:
#             query = query.filter(available_until__lte=datetime.strptime(available_until, "%Y-%m-%d"))

#     if min_rating:
#         query = query.filter(rating__gte=int(min_rating))

#     if max_price:
#         query = query.filter(daily_price__lte=Decimal(max_price)) #larger then 

#     # Distance Calculation using Equirectangular approximation
#     R = 6371 

#     if distance_from:
#         # Get latitude and longitude for the given building name
#         reference_lat, reference_lon, _ = geocode_address(distance_from)

#         if reference_lat is not None and reference_lon is not None:
#             accommodations_with_distance = []
#             for accommodation in query:
#                 if accommodation.latitude is None or accommodation.longitude is None:
#                     continue  

#                 lat1, lon1 = math.radians(reference_lat), math.radians(reference_lon)
#                 lat2, lon2 = math.radians(accommodation.latitude), math.radians(accommodation.longitude)
#                 x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
#                 y = (lat2 - lat1)
#                 d = math.sqrt(x*x + y*y) * R  # Distance in km
#                 accommodations_with_distance.append((d, accommodation))

#             # Sort accommodations by increasing distance
#             accommodations_with_distance.sort(key=lambda item: item[0])
            
#             # Convert results to JSON response with distance included
#             results = [
#                 {
#                     'id': acc.id,
#                     'type': acc.type,
#                     'address': acc.address,
#                     'beds': acc.beds,
#                     'bedrooms': acc.bedrooms,
#                     'rating': acc.rating,
#                     'daily_price': acc.daily_price,
#                     'available_from': acc.available_from,
#                     'available_until': acc.available_until,
#                     'distance_km': round(d, 2),
#                 }
#                 for d, acc in accommodations_with_distance
#             ]
#         else:
#             results = {"error": "Invalid location specified"}
#     else:
#         results =list(query.values('id', 'type', 'address', 'beds', 'bedrooms', 'rating', 'daily_price', 'available_from', 'available_until'))
    
#     return Response(results)

@api_view(['GET', 'POST'])
def add_accommodation(request):
    """
    Add a new accommodation with a default HTML form.
    GET method renders the form, POST processes the form submission.
    """
    if request.method == 'POST':
        serializer = AccommodationSerializer(data=request.data)
        if serializer.is_valid():
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
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        # For GET requests, just return an empty serializer to render the form
        serializer = AccommodationSerializer()
        return Response(serializer.initial_data)