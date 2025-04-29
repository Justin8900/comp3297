from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import University, PropertyOwner, Member, Specialist, Accommodation, Reservation, Rating
from ..serializers import RatingSerializer # Ensure this import exists
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
        # Assumes router basename 'rating'
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
        # Use response data or fetch member from DB if serializer includes it
        # Assuming RatingSerializer includes member_uid or similar
        # Adjust assertion based on your RatingSerializer
        # self.assertEqual(response.data['member_uid'], self.hkust_member.uid) # Example if serializer returns uid

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
        # print("Ratings in DB:", Rating.objects.filter(reservation=self.res_cu_completed, reservation__member=self.cu_member).exists())
        # print("GET response:", response.status_code, response.data)
        # print("Ratings returned (results):", response.data.get('results', []))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1, f"Expected 1 rating, got {len(response.data['results'])}: {response.data['results']}")
        self.assertEqual(response.data['results'][0]['score'], 4)
        self.assertEqual(response.data['results'][0]['comment'], "Good stay!")
        self.assertEqual(response.data['results'][0]['member_uid'], self.cu_member.uid)
    
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