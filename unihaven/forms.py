from django import forms
from .models import Accommodation, PropertyOwner

class AccommodationForm(forms.ModelForm):
    TYPE_CHOICES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('villa', 'Villa'),
        ('studio', 'Studio'),
        ('hostel', 'Hostel'),
    ]
    
    type = forms.ChoiceField(choices=TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    address = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    available_from = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    available_until = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    beds = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    bedrooms = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    rating = forms.IntegerField(min_value=0, max_value=5, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    daily_price = forms.DecimalField(min_value=0.01, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    
    # Owner fields
    owner = forms.ModelChoiceField(
        queryset=PropertyOwner.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select an existing owner (or create new)"
    )
    new_owner_name = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="New Owner Name"
    )
    new_owner_contact = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="New Owner Contact"
    )
    
    class Meta:
        model = Accommodation
        fields = ['type', 'address', 'available_from', 'available_until', 
                  'beds', 'bedrooms', 'rating', 'daily_price', 'owner']
        
    def clean(self):
        cleaned_data = super().clean()
        owner = cleaned_data.get('owner')
        new_owner_name = cleaned_data.get('new_owner_name')
        new_owner_contact = cleaned_data.get('new_owner_contact')
        
        # Check that either owner is selected or new owner details are provided
        if not owner and not (new_owner_name and new_owner_contact):
            raise forms.ValidationError("Either select an existing owner or provide details for a new owner")
            
        # Check available dates
        available_from = cleaned_data.get('available_from')
        available_until = cleaned_data.get('available_until')
        if available_from and available_until and available_until <= available_from:
            raise forms.ValidationError("Available until date must be after available from date")
            
        return cleaned_data
