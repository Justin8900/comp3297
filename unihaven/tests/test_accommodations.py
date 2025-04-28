from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from ..models import Accommodation, University, PropertyOwner, Specialist, Member 
from unittest.mock import patch

class AccommodationUpdateTests(APITestCase):
    "Tests for partial update accomodation."
    @classmethod
    @patch('unihaven.utils.geocoding.geocode_address')
    def setUpTestData(cls, mock_geocode):
        """Set up data for accommodation update tests."""
        mock_geocode.return_value = (1.0, 1.0, 'Mocked Geo Address for Update')

        # Create Universities
        cls.hku = University.objects.create(code='HKU', name='University of Hong Kong')
        cls.cu = University.objects.create(code='CU', name='Chinese University of Hong Kong')
        cls.hkust = University.objects.create(code='HKUST', name='Hong Kong University of Science and Technology')

        # Create Owner
        cls.owner = PropertyOwner.objects.create(name='Test Owner Update', phone_no='222')

        # Create Users for Specialists and Members
        cls.hku_spec_user = User.objects.create_user(username='hku_spec_patch', email='hku_patch@test.com', password='password')
        cls.cu_spec_user = User.objects.create_user(username='cu_spec_patch', email='cu_patch@test.com', password='password')
        cls.hku_mem_user = User.objects.create_user(username='hku_mem_patch', email='hku_mem_patch@test.com', password='password')

        # Create Specialists
        cls.hku_specialist = Specialist.objects.create(name='HKU Spec Patch', university=cls.hku, user=cls.hku_spec_user)
        cls.cu_specialist = Specialist.objects.create(name='CU Spec Patch', university=cls.cu, user=cls.cu_spec_user)

        # Create Member (Remove user link if Member model doesn't have it)
        cls.hku_member = Member.objects.create(uid='patchmem1', name='Patch Member', university=cls.hku)

        # Create initial Accommodation (linked only to HKU) for testing PATCH
        cls.acc_to_patch = Accommodation.objects.create(
            type='studio', address='5 Bonham Road, Mid-Levels', flat_number='P1', floor_number='P',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=1, bedrooms=1, daily_price='90.00', owner=cls.owner
        )
        cls.acc_to_patch.available_at_universities.add(cls.hku)
        cls.acc_to_patch.update_geocoding() # Call geocoding after creation

        # URL for detail view (PATCH target) - assumes router basename 'accommodation'
        cls.url_detail = reverse('accommodation-detail', kwargs={'pk': cls.acc_to_patch.pk})

    # Helper to format URL with role
    def _get_url(self, role_str):
        return f"{self.url_detail}?role={role_str}"

    # --- Test Cases ---

    def test_patch_non_m2m_field(self):
        """
        WHITE-BOX TARGET: Branch 1 (False) in partial_update.
        Update only 'daily_price', not 'available_at_universities'.
        Role: HKU Specialist (managing uni).
        Expect: 200 OK, price updated, universities unchanged.
        """
        role = f"hku:specialist:{self.hku_specialist.id}"
        url = self._get_url(role)
        data = {'daily_price': '95.00'}
        # Authentication note: Assuming DEFAULT_AUTHENTICATION_CLASSES=[] is set for testing
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.acc_to_patch.refresh_from_db()
        self.assertEqual(float(self.acc_to_patch.daily_price), 95.00)
        self.assertCountEqual(
            [uni.code for uni in self.acc_to_patch.available_at_universities.all()],
            ['HKU']
        )

    def test_patch_add_own_university(self):
        """
        WHITE-BOX TARGET: Branch 4 (False -> Path B) in partial_update validation loop.
        Role: CU Specialist (not currently managing).
        Action: Add 'CU' to 'available_at_universities'.
        Expect: 200 OK, 'CU' added.
        """
        role = f"cu:specialist:{self.cu_specialist.id}"
        url = self._get_url(role)
        data = {'available_at_universities': ['HKU', 'CU']} # Request includes current + new
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.acc_to_patch.refresh_from_db()
        self.assertCountEqual(
            [uni.code for uni in self.acc_to_patch.available_at_universities.all()],
            ['HKU', 'CU']
        )

    def test_patch_add_other_university_denied(self):
        """
        WHITE-BOX TARGET: Branch 4 (True -> Path A) in partial_update validation loop.
        Role: HKU Specialist (managing).
        Action: Try to add 'HKUST' (not their own uni).
        Expect: 403 Forbidden.
        """
        role = f"hku:specialist:{self.hku_specialist.id}"
        url = self._get_url(role)
        data = {'available_at_universities': ['HKU', 'HKUST']} # Request includes current + invalid new
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        # Check the specific error message from the view
        self.assertIn(f"Specialist from 'hku' cannot add university 'hkust'", str(response.data.get('detail', '')))
        self.acc_to_patch.refresh_from_db()
        # Verify HKUST was not added
        self.assertCountEqual(
            [uni.code for uni in self.acc_to_patch.available_at_universities.all()],
            ['HKU']
        )

    def test_patch_member_role_denied(self):
        """
        WHITE-BOX TARGET: Coverage of get_permissions preventing member PATCH.
        Role: HKU Member.
        Action: Attempt to update price.
        Expect: 403 Forbidden (blocked by IsSpecialistManagingAccommodation).
        """
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_url(role)
        data = {'daily_price': '98.00'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        # Check message relates to needing specialist role (from permission class)
        self.assertIn("requires a specialist role", str(response.data.get('detail', '')).lower())

    def test_patch_invalid_role_format_denied(self):
        """
        WHITE-BOX TARGET: Branch 2 (PermissionDenied Path E) in partial_update.
        Role: Invalid format.
        Action: Attempt to add universities.
        Expect: 403 Forbidden (from get_role_or_403 caught in partial_update).
        """
        role = "hku-specialist-invalid" # Bad format
        url = f"{self.url_detail}?role={role}" # Manual URL format
        data = {'available_at_universities': ['HKU', 'CU']}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
        # Check message relates to needing specialist role (from permission class)
        self.assertIn("requires a specialist role", str(response.data.get('detail', '')).lower())

class AccommodationBaseTestCase(APITestCase):
    @classmethod
    @patch('unihaven.utils.geocoding.geocode_address')
    def setUpTestData(cls, mock_geocode):
        """Set up data for accommodation tests."""
        mock_geocode.return_value = (1.0, 1.0, 'Mocked Geo Address for Base')

        # Create Universities
        cls.hku = University.objects.create(code='HKU', name='University of Hong Kong')
        cls.cu = University.objects.create(code='CU', name='Chinese University of Hong Kong')
        cls.hkust = University.objects.create(code='HKUST', name='Hong Kong University of Science and Technology')

        # Create Owner
        cls.owner = PropertyOwner.objects.create(name='Acc Test Owner', phone_no='555')

        # Create Members
        cls.hku_member = Member.objects.create(uid='accmem1', name='Acc Member HKU', university=cls.hku)
        cls.cu_member = Member.objects.create(uid='accmem2', name='Acc Member CU', university=cls.cu)
        cls.hkust_member = Member.objects.create(uid='accmem3', name='Acc Member HKUST', university=cls.hkust)

        # Create Specialists (need user association for login/role check if applicable)
        # For simplicity, assuming role check doesn't require user login for these tests
        # If login is needed, create User instances as in reservation tests
        cls.hku_specialist = Specialist.objects.create(name='Acc Spec HKU', university=cls.hku)
        cls.cu_specialist = Specialist.objects.create(name='Acc Spec CU', university=cls.cu)

        # Create Accommodations
        cls.acc1_hku = Accommodation.objects.create(
            type='studio', address='2 Sassoon Road, Pok Fu Lam', owner=cls.owner,
            flat_number='S1A', floor_number='1SA',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=1, bedrooms=1, daily_price='110.00'
            )
        cls.acc1_hku.available_at_universities.add(cls.hku)
        cls.acc1_hku.update_geocoding() # Call geocoding after creation

        cls.acc2_cu = Accommodation.objects.create(
            type='apartment', address='18 Taipo Road, Ma Liu Shui', owner=cls.owner,
            flat_number='A2A', floor_number='2AA',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=2, bedrooms=1, daily_price='190.00'
            )
        cls.acc2_cu.available_at_universities.add(cls.cu)
        cls.acc2_cu.update_geocoding() # Call geocoding after creation

        cls.acc3_hku_cu = Accommodation.objects.create(
            type='shared', address='3 Garden Road, Central', owner=cls.owner,
            flat_number='SH3A', floor_number='3SA',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=3, bedrooms=2, daily_price='170.00'
            )
        cls.acc3_hku_cu.available_at_universities.add(cls.hku, cls.cu)
        cls.acc3_hku_cu.update_geocoding() # Call geocoding after creation

        cls.acc4_all = Accommodation.objects.create(
            type='house', address='7 Repulse Bay Road, Repulse Bay', owner=cls.owner,
            flat_number='H4A', floor_number='4HA',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=4, bedrooms=3, daily_price='250.00'
            )
        cls.acc4_all.available_at_universities.add(cls.hku, cls.cu, cls.hkust)
        cls.acc4_all.update_geocoding() # Call geocoding after creation

    def _get_list_url(self, role_str):
        # Assumes router basename 'accommodation'
        base_url = reverse('accommodation-list')
        return f"{base_url}?role={role_str}"

    def _get_detail_url(self, role_str, pk):
        # Assumes router basename 'accommodation'
        base_url = reverse('accommodation-detail', kwargs={'pk': pk})
        return f"{base_url}?role={role_str}"

class AccommodationListPermissionsTests(AccommodationBaseTestCase):
    "Tests for listing accommodations based on user roles."

    def test_member_can_view_own_uni_accommodations(self):
        """Verify HKU member can list accommodations available at HKU."""
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_list_url(role)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        result_ids = {item['id'] for item in results}
        # Should see acc1_hku, acc3_hku_cu, acc4_all
        self.assertIn(self.acc1_hku.id, result_ids)
        self.assertNotIn(self.acc2_cu.id, result_ids)
        self.assertIn(self.acc3_hku_cu.id, result_ids)
        self.assertIn(self.acc4_all.id, result_ids)
        self.assertEqual(len(result_ids), 3)

    def test_specialist_can_view_own_uni_accommodations(self):
        """Verify CU specialist can list accommodations available at CU."""
        role = f"cu:specialist:{self.cu_specialist.id}"
        url = self._get_list_url(role)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        result_ids = {item['id'] for item in results}
        # Should see acc2_cu, acc3_hku_cu, acc4_all
        self.assertNotIn(self.acc1_hku.id, result_ids)
        self.assertIn(self.acc2_cu.id, result_ids)
        self.assertIn(self.acc3_hku_cu.id, result_ids)
        self.assertIn(self.acc4_all.id, result_ids)
        self.assertEqual(len(result_ids), 3)

    def test_anonymous_user_cannot_list_accommodations(self):
        """Verify anonymous user gets 403 Forbidden when listing without role."""
        url = reverse('accommodation-list') # No role provided
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class AccommodationDetailPermissionsTests(AccommodationBaseTestCase):
    "Tests for retrieving accommodation details based on user roles."
    def test_member_can_view_own_uni_accommodation_detail(self):
        """Verify HKU member can view detail of an accommodation available at HKU."""
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_detail_url(role, self.acc3_hku_cu.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.acc3_hku_cu.id)

    def test_member_cannot_view_other_uni_accommodation_detail(self):
        """Verify HKU member cannot view detail of an accommodation only available at CU."""
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_detail_url(role, self.acc2_cu.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_specialist_can_view_own_uni_accommodation_detail(self):
        """Verify CU specialist can view detail of an accommodation available at CU."""
        role = f"cu:specialist:{self.cu_specialist.id}"
        url = self._get_detail_url(role, self.acc4_all.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.acc4_all.id)

    def test_specialist_cannot_view_other_uni_accommodation_detail(self):
        """Verify CU specialist cannot view detail of an accommodation only at HKU."""
        role = f"cu:specialist:{self.cu_specialist.id}"
        url = self._get_detail_url(role, self.acc1_hku.id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_cannot_view_accommodation_detail(self):
        """Verify anonymous user gets 403 Forbidden for detail view without role."""
        url = reverse('accommodation-detail', kwargs={'pk': self.acc1_hku.id}) # No role
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class AccommodationEndpointTests(AccommodationBaseTestCase):

    def test_create_accommodation(self):
        """Verify CU specialist can create accommodations."""
        role = f"cu:specialist:{self.cu_specialist.id}"
        url = self._get_list_url(role)
        data = {
            'type': 'apartment',
            'address': '123 Test',
            'room_number': '12A',
            'flat_number': '23',
            'floor_number': '3',
            'available_from': '2025-04-28',
            'available_until': '2025-05-28',
            'beds': 3,
            'bedrooms': 2,
            'daily_price': '250', 
            'owner_id': self.owner.id,  
            'available_at_universities': ["CU"]  
        }
        response = self.client.post(url, data, format='json')
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
    def test_update_accommodation(self):
        role = f"cu:specialist:{self.cu_specialist.id}"
        url = self._get_detail_url(role, self.acc4_all.id)
        data = {
            'type': 'apartment',
            'address': '123 Update',
            'room_number': '12A',
            'flat_number': '23',
            'floor_number': '3',
            'available_from': '2025-04-28',
            'available_until': '2025-05-28',
            'beds': 3,
            'bedrooms': 2,
            'daily_price': '250', 
            'owner_id': self.owner.id,  
            'available_at_universities': ["CU"]  
        }  
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_accommodation(self):
        role = f"cu:specialist:{self.cu_specialist.id}"
        url = self._get_detail_url(role, self.acc4_all.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_nearby_accommodations(self):
        response = self.client.get(f"accommodations/nearby/?location_name=CUHK Campus?role=cu:specialist:{self.cu_specialist.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.data)