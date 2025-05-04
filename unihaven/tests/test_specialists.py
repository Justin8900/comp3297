from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from unihaven.models import Specialist, University
from django.contrib.auth.models import User


class SpecialistTests(APITestCase):
    def setUp(self):
         # Create Universities
        self.hku = University.objects.create(code='HKU', name='University of Hong Kong')
        self.cu = University.objects.create(code='CU', name='Chinese University of Hong Kong')
        self.hkust = University.objects.create(code='HKUST', name='Hong Kong University of Science and Technology')
        
        # Create Users for Specialists
        self.hku_spec_user = User.objects.create_user(username='hku_spec_patch', email='hku_patch@test.com', password='password')
        self.cu_spec_user1 = User.objects.create_user(username='cu_spec_patch', email='cu_patch@test.com', password='password')
        self.cu_spec_user2 = User.objects.create_user(username='cu_test', email='cu_test@test.com', password='password')

        # Create Specialists
        self.hku_specialist = Specialist.objects.create(name='HKU Spec', university=self.hku, user=self.hku_spec_user)
        self.cu_specialist1 = Specialist.objects.create(name='CU Spec', university=self.cu, user=self.cu_spec_user1)
        self.cu_specialist2 = Specialist.objects.create(name='cu_test', university=self.cu, user=self.cu_spec_user2)
    
    def test_list(self):
        """Test the list of specialists."""
        response= self.client.get(f"/specialists/?role=cu:specialist:{self.cu_specialist1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['name'], self.cu_specialist1.name)
        self.assertEqual(response.data['results'][0]['university'], self.cu_specialist1.university.code)
        self.assertEqual(response.data['results'][1]['name'], self.cu_specialist2.name)
        self.assertEqual(response.data['results'][1]['university'], self.cu_specialist2.university.code)
        self.assertEqual(response.data['results'][0]['id'], self.cu_specialist1.id)
        self.assertEqual(response.data['results'][1]['id'], self.cu_specialist2.id)
    
    def test_retrieve(self):
        """Test the retrieve of a specialist."""
        response = self.client.get(f"/specialists/{self.cu_specialist2.id}/?role=cu:specialist:{self.cu_specialist1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.cu_specialist2.id)
        self.assertEqual(response.data['name'], self.cu_specialist2.name)
        self.assertEqual(response.data['university'], self.cu_specialist2.university.code)

    def test_create_specialist_by_specialist(self):
        """Test creating a new specialist by an existing specialist."""
        url = f"/specialists/?role=cu:specialist:{self.cu_specialist1.id}"
        data = {
            "name": "New CU Specialist",
            "email": "new.cu.spec@cu.hk", 
            "phone": "11223344"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "New CU Specialist")
        self.assertEqual(response.data['university'], self.cu.code) # Should match creator's uni

        # Verify the specialist exists in the database and belongs to CU
        new_spec_exists = Specialist.objects.filter(
            name="New CU Specialist",
            university=self.cu
        ).exists()
        self.assertTrue(new_spec_exists)

        # Verify the count for CU specialists increased
        cu_specialist_count = Specialist.objects.filter(university=self.cu).count()
        self.assertEqual(cu_specialist_count, 3) # Started with 2 CU specialists