from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import University, PropertyOwner, Member, Specialist, Accommodation, Reservation, Rating
from unittest.mock import patch

class RatingCreateTests(APITestCase):

    @classmethod
    @patch('unihaven.utils.geocoding.geocode_address')
    def setUpTestData(cls, mock_geocode):
        """Set up data for rating tests."""
        mock_geocode.return_value = (1.0, 1.0, 'Mocked Geo Address for Ratings')

        # Create Universities
        cls.hku = University.objects.create(code='HKU', name='University of Hong Kong')
        cls.cu = University.objects.create(code='CU', name='Chinese University of Hong Kong')
        cls.hkust = University.objects.create(code='HKUST', name='Hong Kong University of Science and Technology')

        # Create Owner
        cls.owner = PropertyOwner.objects.create(name='Rating Test Owner', phone_no='333')

        # Create Users for Members
        cls.hku_mem_user = User.objects.create_user(username='hku_mem_rate', email='hku_rate@test.com', password='password')
        cls.hkust_mem_user = User.objects.create_user(username='hkust_mem_rate', email='hkust_rate@test.com', password='password')
        cls.cu_mem_user = User.objects.create_user(username='cu_mem_rate', email='cu_rate@test.com', password='password')
        # Create Members
        cls.hku_member = Member.objects.create(uid='ratemem1', name='Rate Member HKU', university=cls.hku)
        cls.hkust_member = Member.objects.create(uid='ratemem2', name='Rate Member HKUST', university=cls.hkust)
        cls.cu_member = Member.objects.create(uid='ratemem3', name='Rate Member CU', university=cls.cu)

        #Create Specialists 
        cls.specialist_user = User.objects.create_user(username='spec_rate', email='spec_rate@test.com', password='password')
        cls.specialist = Specialist.objects.create(name='Rating Specialist', university=cls.cu)
       
        # Create Accommodation
        cls.acc_for_rating = Accommodation.objects.create(
            type='apartment', address='10 Hollywood Road, Central', owner=cls.owner,
            flat_number='R1', floor_number='GR',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=2, bedrooms=1, daily_price='150.00'
        )
        cls.acc_for_rating.available_at_universities.add(cls.hku, cls.hkust,cls.cu)
        cls.acc_for_rating.update_geocoding() # Call geocoding after creation

        # Create Reservations
        cls.res_hku_pending = Reservation.objects.create(
            member=cls.hku_member, accommodation=cls.acc_for_rating, university=cls.hku,
            start_date='2025-10-01', end_date='2025-10-05', status='pending'
        )
        cls.res_hkust_completed = Reservation.objects.create(
            member=cls.hkust_member, accommodation=cls.acc_for_rating, university=cls.hkust,
            start_date='2025-09-01', end_date='2025-09-05', status='completed'
        )

        cls.res_cu_completed = Reservation.objects.create(
            member=cls.cu_member, accommodation=cls.acc_for_rating, university=cls.cu,
            start_date='2025-08-01', end_date='2025-08-05', status='completed'
        )

    def test_member_can_rate_own_completed_reservation(self):
        """Verify a member can rate their own completed reservation."""
        role = f"hkust:member:{self.hkust_member.uid}"
        url = reverse('rating-list') # POST to list endpoint
        url_with_role = f"{url}?role={role}"
        data = {
            "reservation": self.res_hkust_completed.id,
            "score": 4,
            "comment": "Good stay!"
        }
        response = self.client.post(url_with_role, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['score'], 4)
        self.assertEqual(response.data['comment'], "Good stay!")

        # Verify rating exists in DB linked correctly
        self.assertTrue(Rating.objects.filter(reservation=self.res_hkust_completed, reservation__member=self.hkust_member).exists())
        rating = Rating.objects.get(reservation=self.res_hkust_completed)
        self.assertEqual(rating.score, 4)
        self.assertEqual(rating.comment, "Good stay!")

    def test_member_cannot_rate_pending_reservation(self):
        """Verify rating fails if reservation is not completed."""
        role = f"hku:member:{self.hku_member.uid}"
        url = reverse('rating-list')
        url_with_role = f"{url}?role={role}"
        data = {"reservation": self.res_hku_pending.id, "score": 5}
        response = self.client.post(url_with_role, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check the specific validation error message from the serializer or view
        self.assertIn("only rate completed reservations", str(response.data).lower())

    def test_member_cannot_rate_others_reservation(self):
        """Verify rating fails if member doesn't own the reservation."""
        role = f"hku:member:{self.hku_member.uid}" # HKU member
        url = reverse('rating-list')
        url_with_role = f"{url}?role={role}"
        data = {"reservation": self.res_hkust_completed.id, "score": 3} # HKUST's completed res
        response = self.client.post(url_with_role, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
         # Check the specific validation error message from the serializer or view
        self.assertIn("only rate your own reservations", str(response.data).lower())

    def test_member_cannot_rate_twice(self):
        """Verify a member cannot rate the same completed reservation twice."""
        # First rating (successful)
        role = f"hkust:member:{self.hkust_member.uid}"
        url = reverse('rating-list')
        url_with_role = f"{url}?role={role}"
        data1 = {"reservation": self.res_hkust_completed.id, "score": 4, "comment": "First rating"}
        response1 = self.client.post(url_with_role, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second attempt (should fail)
        data2 = {"reservation": self.res_hkust_completed.id, "score": 1, "comment": "Second attempt"}
        response2 = self.client.post(url_with_role, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("this reservation has already been rated", str(response2.data).lower())

    def test_list_ratings(self):
        """Listing ratings for a members."""
        # Create a rating
        role = f"cu:member:{self.cu_member.uid}"
        url = reverse('rating-list')
        url_with_role = f"{url}?role={role}"
        data = {"reservation": self.res_cu_completed.id, "score": 4, "comment": "Good stay!"}
        self.client.post(url_with_role, data, format='json')

        response = self.client.get(url_with_role)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list) # No pagination
        self.assertEqual(len(response.data), 1, f"Expected 1 rating, got {len(response.data)}: {response.data}")
        if response.data:
            self.assertEqual(response.data[0]['score'], 4)
            self.assertEqual(response.data[0]['comment'], "Good stay!")
            self.assertEqual(response.data[0]['member_uid'], self.cu_member.uid)
    
    def test_delete_rating_specialist(self):
        """Verify that a specialist can delete a rating, but a member cannot."""
        # Create a rating
        member_role = f"cu:member:{self.cu_member.uid}"
        url = reverse('rating-list')
        url_with_role = f"{url}?role={member_role}"
        data = {
            "reservation": self.res_cu_completed.id,
            "score": 4,
            "comment": "Good stay at CU!"
        }
        post_response = self.client.post(url_with_role, data, format='json')
        self.assertEqual(post_response.status_code, status.HTTP_201_CREATED, post_response.data)
        rating_id = post_response.data['id']

        # Verify rating exists in DB
        self.assertTrue(Rating.objects.filter(reservation=self.res_cu_completed, reservation__member=self.cu_member).exists())
        rating = Rating.objects.get(reservation=self.res_cu_completed)
        self.assertEqual(rating.score, 4)
        self.assertEqual(rating.comment, "Good stay at CU!")

        # Attempt to delete as a member (expected to fail)
        delete_url = reverse('rating-detail', kwargs={'pk': rating_id})
        delete_url_member = f"{delete_url}?role={member_role}"
        response_member = self.client.delete(delete_url_member)
        print("Member delete response:", response_member.status_code, response_member.data)
        self.assertEqual(response_member.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Rating.objects.filter(id=rating_id).exists(), "Rating should not be deleted by member")

        # Delete as a specialist (expected to succeed)
        specialist_role = f"cu:specialist:{self.specialist.id}"
        delete_url_specialist = f"{delete_url}?role={specialist_role}"
        response_specialist = self.client.delete(delete_url_specialist)
        print("Specialist delete response:", response_specialist.status_code, response_specialist.data)
        self.assertEqual(response_specialist.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Rating.objects.filter(id=rating_id).exists(), "Rating should be deleted by specialist")

# Define base setup needed for visibility tests independently
class RatingVisibilityBaseTestCase(APITestCase):
    @classmethod
    @patch('unihaven.utils.geocoding.geocode_address')
    def setUpTestData(cls, mock_geocode):
        mock_geocode.return_value = (1.0, 1.0, 'Mocked Geo Addr Visibility')
        cls.hku = University.objects.create(code='HKU', name='HKU')
        cls.cu = University.objects.create(code='CU', name='CU')
        cls.hkust = University.objects.create(code='HKUST', name='HKUST')
        cls.owner = PropertyOwner.objects.create(name='Rating Vis Owner', phone_no='123')
        # Users
        cls.hku_mem_user = User.objects.create_user(username='hku_vis', password='pw')
        cls.cu_mem_user = User.objects.create_user(username='cu_vis', password='pw')
        cls.hkust_mem_user = User.objects.create_user(username='hkust_vis', password='pw')
        cls.cu_spec_user = User.objects.create_user(username='cu_spec_vis', password='pw')
        # Members
        cls.hku_member = Member.objects.create(uid='hkuvis1', name='HKU Vis Mem', university=cls.hku)
        cls.cu_member = Member.objects.create(uid='cuvis1', name='CU Vis Mem', university=cls.cu)
        cls.hkust_member = Member.objects.create(uid='hkustvis1', name='HKUST Vis Mem', university=cls.hkust)
        # Specialist
        cls.cu_specialist = Specialist.objects.create(name='CU Vis Spec', university=cls.cu, user=cls.cu_spec_user)
        # Accommodations
        cls.acc_cu_1 = Accommodation.objects.create(
            type='studio', address='CU Acc 1', owner=cls.owner,
            available_from='2025-01-01', available_until='2025-12-31', beds=1, bedrooms=1, daily_price='100'
        )
        cls.acc_cu_1.available_at_universities.add(cls.cu)
        cls.acc_cu_1.update_geocoding()
        cls.acc_cu_2 = Accommodation.objects.create(
            type='studio', address='CU Acc 2', owner=cls.owner,
            available_from='2025-01-01', available_until='2025-12-31', beds=1, bedrooms=1, daily_price='110'
        )
        cls.acc_cu_2.available_at_universities.add(cls.cu)
        cls.acc_cu_2.update_geocoding()
        cls.acc_hku = Accommodation.objects.create(
            type='studio', address='HKU Acc 1', owner=cls.owner,
            available_from='2025-01-01', available_until='2025-12-31', beds=1, bedrooms=1, daily_price='120'
        )
        cls.acc_hku.available_at_universities.add(cls.hku)
        cls.acc_hku.update_geocoding()
        # Completed Reservations (one per uni for simplicity)
        cls.res_cu_1 = Reservation.objects.create(member=cls.cu_member, accommodation=cls.acc_cu_1, university=cls.cu, start_date='2025-08-01', end_date='2025-08-05', status='completed')
        cls.res_cu_2 = Reservation.objects.create(member=cls.cu_member, accommodation=cls.acc_cu_2, university=cls.cu, start_date='2025-08-10', end_date='2025-08-15', status='completed')
        cls.res_hku = Reservation.objects.create(member=cls.hku_member, accommodation=cls.acc_hku, university=cls.hku, start_date='2025-09-01', end_date='2025-09-05', status='completed')
        # Ratings
        cls.rating_cu_1 = Rating.objects.create(reservation=cls.res_cu_1, score=4, comment='CU Rating 1')
        cls.rating_cu_2 = Rating.objects.create(reservation=cls.res_cu_2, score=2, comment='CU Rating 2')
        cls.rating_hku = Rating.objects.create(reservation=cls.res_hku, score=5, comment='HKU Rating')

# Remove inheritance from RatingCreateTests
class RatingVisibilityTests(RatingVisibilityBaseTestCase): 

    def test_member_can_list_all_own_uni_ratings(self):
        """Verify a member sees all ratings from their university."""
        role = f"cu:member:{self.cu_member.uid}"
        url = reverse('rating-list') + f"?role={role}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        rating_ids = {r['id'] for r in response.data}
        self.assertIn(self.rating_cu_1.id, rating_ids) # Should see CU rating 1
        self.assertIn(self.rating_cu_2.id, rating_ids) # Should see CU rating 2
        self.assertNotIn(self.rating_hku.id, rating_ids) # Should not see HKU rating
        self.assertEqual(len(rating_ids), 2) # Expect 2 ratings

    def test_member_cannot_list_other_uni_ratings(self):
        """Verify a member cannot list ratings from another university."""
        role = f"hku:member:{self.hku_member.uid}"
        url = reverse('rating-list') + f"?role={role}"
        response = self.client.get(url)
        # Expect 200 OK, but the list should only contain HKU ratings
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list) # No pagination
        rating_ids = {r['id'] for r in response.data}
        self.assertIn(self.rating_hku.id, rating_ids)
        self.assertEqual(len(rating_ids), 1) # Should only see the 1 HKU rating

    def test_member_can_filter_list_by_accommodation(self):
        """Verify a member can filter ratings by accommodation ID."""
        role = f"cu:member:{self.cu_member.uid}"
        url = reverse('rating-list') + f"?role={role}&accommodation_id={self.acc_cu_1.id}" # Filter for acc_cu_1
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        rating_ids = {r['id'] for r in response.data}
        self.assertIn(self.rating_cu_1.id, rating_ids) # Rating for acc_cu_1
        self.assertNotIn(self.rating_cu_2.id, rating_ids) # Rating for acc_cu_2
        self.assertEqual(len(rating_ids), 1)

    def test_member_can_retrieve_other_member_rating_same_uni(self):
        """Verify member can retrieve another member's rating from same uni."""
        # Create another CU member and rating for this test
        other_cu_mem_user = User.objects.create_user(username='other_cu', password='pw')
        other_cu_mem = Member.objects.create(uid='other_cu_mem', name='Other CU', university=self.cu)
        # Use acc_cu_2 for the other member
        res_other = Reservation.objects.create(
            member=other_cu_mem, accommodation=self.acc_cu_2, university=self.cu,
            start_date='2025-06-01', end_date='2025-06-05', status='completed'
        )
        rating_other = Rating.objects.create(reservation=res_other, score=1)

        role = f"cu:member:{self.cu_member.uid}" # Original CU member
        url = reverse('rating-detail', kwargs={'pk': rating_other.id}) + f"?role={role}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['id'], rating_other.id)
        self.assertEqual(response.data['score'], 1)

    def test_member_cannot_retrieve_other_uni_rating(self):
        """Verify member cannot retrieve a rating from another university."""
        role = f"hku:member:{self.hku_member.uid}" # HKU member
        url = reverse('rating-detail', kwargs={'pk': self.rating_cu_1.id}) + f"?role={role}" # Use rating_cu_1 ID
        response = self.client.get(url)
        # Expect 404 Not Found because the queryset should filter out other uni ratings before permissions hit
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # self.assertIn("action requires role from university 'cu'", str(response.data).lower())

    # Keep test_delete_rating_specialist, it should work with the new setup base
    def test_delete_rating_specialist(self):
        """Verify that a specialist can delete a rating, but a member cannot."""
        rating_to_delete = self.rating_cu_1 # Use a rating created in the base setup
        member_role = f"cu:member:{self.cu_member.uid}"
        specialist_role = f"cu:specialist:{self.cu_specialist.id}"
        delete_url = reverse('rating-detail', kwargs={'pk': rating_to_delete.id})

        # Attempt to delete as a member (expected to fail)
        delete_url_member = f"{delete_url}?role={member_role}"
        response_member = self.client.delete(delete_url_member)
        self.assertEqual(response_member.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Rating.objects.filter(id=rating_to_delete.id).exists(), "Rating should not be deleted by member")

        # Delete as a specialist (expected to succeed)
        delete_url_specialist = f"{delete_url}?role={specialist_role}"
        response_specialist = self.client.delete(delete_url_specialist)
        self.assertEqual(response_specialist.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Rating.objects.filter(id=rating_to_delete.id).exists(), "Rating should be deleted by specialist")
