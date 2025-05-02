from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth.models import User
from unihaven.models import University, Specialist, PropertyOwner

class PropertyOwnerTests(APITestCase):
    def setUp(self):
        """Set up the test environment."""
        self.hku = University.objects.create(code='HKU', name='University of Hong Kong')
        self.specialist_user = User.objects.create_user(username='spec1', password='password')
        self.specialist = Specialist.objects.create(name='HKU Specialist', university=self.hku, user=self.specialist_user)
        self.role = f"hku:specialist:{self.specialist.id}"
        # Create owner without email initially
        self.owner = PropertyOwner.objects.create(name='Test Owner', phone_no='12345678')

    def test_list_property_owners(self):
        """Test listing property owners."""
        url = reverse('property-owner-list') + f"?role={self.role}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if email field exists (should be null initially)
        self.assertIn('email', response.data['results'][0])
        self.assertIsNone(response.data['results'][0]['email'])

    def test_create_property_owner(self):
        """Test creating a new property owner with email."""
        url = reverse('property-owner-list') + f"?role={self.role}"
        data = {'name': 'New Owner', 'phone_no': '98765432', 'email': 'newowner@test.com'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newowner@test.com')

    def test_create_property_owner_no_email(self):
        """Test creating a new property owner without email."""
        url = reverse('property-owner-list') + f"?role={self.role}"
        data = {'name': 'Another Owner', 'phone_no': '55554444'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['email']) # Email should be null

    def test_retrieve_property_owner(self):
        '""Test retrieving a property owner."""'
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.owner.name)
        self.assertIn('email', response.data) # Check email field exists
        self.assertIsNone(response.data['email']) # Should be null initially

    def test_update_property_owner(self):
        """Test updating a property owner including email."""
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        data = {'name': 'Updated Owner', 'phone_no': '11111111', 'email': 'updated@test.com'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Owner')
        self.assertEqual(response.data['email'], 'updated@test.com')

    def test_partial_update_property_owner_email(self):
        """Test partial update of a property owner email only."""
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        data = {'email': 'partial@test.com'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'partial@test.com')
        # Ensure other fields didn't change
        self.assertEqual(response.data['name'], self.owner.name)

    def test_delete_property_owner(self):
        """Test deleting a property owner."""
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PropertyOwner.objects.filter(id=self.owner.id).exists())
