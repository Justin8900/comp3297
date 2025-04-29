from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from unihaven.models import Specialist, University, Member
from django.contrib.auth.models import User

class MembersTests(APITestCase):
    def setUp(self):
        #Create Universities
        self.hku = University.objects.create(code='HKU', name='University of Hong Kong')
        self.cu = University.objects.create(code='CU', name='Chinese University of Hong Kong')
        self.hkust = University.objects.create(code='HKUST', name='Hong Kong University of Science and Technology')
        # Create Users for Members
        self.hku_mem_user1 = User.objects.create_user(username='hku_mem1', email='hku_mem_patch@test.com', password='password')
        self.cu_mem_user1 = User.objects.create_user(username='cu_mem1', email='cumem1@test.com', password='password')
        self.cu_mem_user2 = User.objects.create_user(username='cu_mem2', email='cumem2@test.com', password='password')
        self.hkust_mem_user1 = User.objects.create_user(username='hkust_mem1', email='hkust_mem_patch@test.com', password='password')

        # Create Users for Specialists
        self.hku_spec_user = User.objects.create_user(username='hku_spec_patch', email='hku_patch@test.com', password='password')
        self.cu_spec_user1 = User.objects.create_user(username='cu_spec_patch', email='cu_patch@test.com', password='password')
        self.cu_spec_user2 = User.objects.create_user(username='cu_test', email='cu_test@test.com', password='password')

        # Create Specialists
        self.hku_specialist = Specialist.objects.create(name='HKU Spec', university=self.hku, user=self.hku_spec_user)
        self.cu_specialist1 = Specialist.objects.create(name='CU Spec', university=self.cu, user=self.cu_spec_user1)
        self.cu_specialist2 = Specialist.objects.create(name='cu_test', university=self.cu, user=self.cu_spec_user2)

        #Create Members
        self.hku_member = Member.objects.create(uid='hku1',name='HKUMem1', university=self.hku, user=self.hku_mem_user1)
        self.cu_member1 = Member.objects.create(uid='cu3',name='CUMem1', university=self.cu, user=self.cu_mem_user1)
        self.cu_member2 = Member.objects.create(uid='cu2',name='CUMem2', university=self.cu, user=self.cu_mem_user2)
        self.hkust_member = Member.objects.create(uid='ust1',name='HKUSTMem1', university=self.hkust, user=self.hkust_mem_user1)

    def test_list(self):
        """Test the list of members."""
        url = reverse('member-list')
        url_with_role = f"{url}?role=cu:specialist:{self.cu_specialist1.id}"
        response = self.client.get(url_with_role)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['name'], self.cu_member1.name)
        self.assertEqual(response.data['results'][0]['university'], self.cu_member1.university.code)
        self.assertEqual(response.data['results'][1]['name'], self.cu_member2.name)
        self.assertEqual(response.data['results'][1]['university'], self.cu_member2.university.code)

    def test_create_member(self):
        """Test create member by specialist."""
        url = reverse('member-list') + f"?role=cu:specialist:{self.cu_specialist1.id}"
        data = {
            "uid": "cu_new",
            "name": "New CU Member",
            "university": "CU",
            "user": self.cu_mem_user1.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "New CU Member")
        self.assertEqual(response.data['university'], "CU")

    def test_retrieve_member(self):
        """Test retrieve member"""
        url = reverse('member-detail', args=[self.cu_member1.uid]) + f"?role=cu:member:{self.cu_member1.uid}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uid'], self.cu_member1.uid)

    def test_update_member(self):
        """Test Update a member by UID"""
        url = reverse('member-detail', args=[self.cu_member1.uid]) + f"?role=cu:member:{self.cu_member1.uid}"
        data = {
            "uid": self.cu_member1.uid,
            "name": "Updated CU Member",
            "university": "CU",
            "user": self.cu_mem_user1.id
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Updated CU Member")

    def test_partial_update_member(self):
        """Tesr partial update a member by UID"""
        url = reverse('member-detail', args=[self.cu_member1.uid]) + f"?role=cu:member:{self.cu_member1.uid}"
        data = {"name": "Partially Updated CU Member"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Partially Updated CU Member")

    def test_delete_member(self):
        """Test delete a member by UID"""
        url = reverse('member-detail', args=[self.cu_member2.uid]) + f"?role=cu:specialist:{self.cu_specialist1.id}"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Member.objects.filter(uid=self.cu_member2.uid).exists())

    def test_list_member_reservations(self):
        """Testing list reservation for a member."""
        url = reverse('member-reservations', args=[self.cu_member1.uid]) + f"?role=cu:member:{self.cu_member1.uid}"
        response = self.client.get(url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])