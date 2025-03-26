from django.shortcuts import render
from django.views.generic import ListView
from .models import *

# Create your views here.

class AccommodationListView(ListView):
    model = Accommodation
    template_name = 'accommodation_list.html'
    context_object_name = 'accommodations'

    def get_queryset(self):
        queryset = super().get_queryset()
        price_min = self.request.GET.get('price_min')
        price_max = self.request.GET.get('price_max')
        location = self.request.GET.get('location')
        no_beds = self.request.GET.get('no_beds')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if price_min:
            queryset = queryset.filter(daily_price__gte=price_min)
        if price_max:
            queryset = queryset.filter(daily_price__lte=price_max)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if no_beds:
            queryset = queryset.filter(no_beds__gte=no_beds)
        if start_date:
            queryset = queryset.filter(start_date__lte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__gte=end_date)

        return queryset
