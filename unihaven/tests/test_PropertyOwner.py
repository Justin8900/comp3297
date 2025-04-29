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
        self.owner = PropertyOwner.objects.create(name='Test Owner', phone_no='12345678')

    def test_list_property_owners(self):
        """Test listing property owners."""
        url = reverse('property-owner-list') + f"?role={self.role}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_property_owner(self):
        """Test creating a new property owner."""
        url = reverse('property-owner-list') + f"?role={self.role}"
        data = {'name': 'New Owner', 'phone_no': '98765432'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_property_owner(self):
        '""Test retrieving a property owner."""'
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.owner.name)

    def test_update_property_owner(self):
        """Test updating a property owner."""
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        data = {'name': 'Updated Owner', 'phone_no': '11111111'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Owner')

    def test_partial_update_property_owner(self):
        """Test partial update of a property owner."""
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        data = {'phone_no': '22222222'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_no'], '22222222')

    def test_delete_property_owner(self):
        """Test deleting a property owner."""
        url = reverse('property-owner-detail', args=[self.owner.id]) + f"?role={self.role}"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PropertyOwner.objects.filter(id=self.owner.id).exists())
