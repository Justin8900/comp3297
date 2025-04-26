from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import University, PropertyOwner, Member, Specialist, Accommodation, Reservation
from unittest.mock import patch

class ReservationBaseTestCase(APITestCase):

    @classmethod
    @patch('unihaven.utils.geocoding.geocode_address')
    def setUpTestData(cls, mock_geocode):
        """Set up common data for reservation tests."""
        # Mock geocode_address to return dummy data
        mock_geocode.return_value = (1.0, 1.0, 'Mocked Geo Address for Tests')
        
        # Create Universities
        cls.hku = University.objects.create(code='HKU', name='University of Hong Kong')
        cls.cu = University.objects.create(code='CU', name='Chinese University of Hong Kong')
        cls.hkust = University.objects.create(code='HKUST', name='Hong Kong University of Science and Technology')

        # Create Owner
        cls.owner = PropertyOwner.objects.create(name='Reservation Test Owner', phone_no='444')

        # Create Users for Specialists and Members
        cls.hku_spec_user = User.objects.create_user(username='hku_spec_res', email='hku_res@test.com', password='password')
        cls.hkust_spec_user = User.objects.create_user(username='hkust_spec_res', email='hkust_res@test.com', password='password')
        cls.hku_mem_user = User.objects.create_user(username='hku_mem_res', email='hku_mem_res@test.com', password='password')
        cls.cu_mem_user = User.objects.create_user(username='cu_mem_res', email='cu_mem_res@test.com', password='password')
        cls.hkust_mem_user = User.objects.create_user(username='hkust_mem_res', email='hkust_mem_res@test.com', password='password')
        cls.cu_spec_user = User.objects.create_user(username='cu_spec_res', email='cu_res@test.com', password='password') # Add user for CU spec

        # Create Specialists
        cls.hku_specialist = Specialist.objects.create(name='HKU Spec Res', university=cls.hku, user=cls.hku_spec_user)
        cls.hkust_specialist = Specialist.objects.create(name='HKUST Spec Res', university=cls.hkust, user=cls.hkust_spec_user)
        cls.cu_specialist = Specialist.objects.create(name='CU Spec Res', university=cls.cu, user=cls.cu_spec_user) # Add CU spec

        # Create Members (and link to users)
        cls.hku_member = Member.objects.create(uid='resmem1', name='Res Member HKU', university=cls.hku, user=cls.hku_mem_user)
        cls.cu_member = Member.objects.create(uid='resmem2', name='Res Member CU', university=cls.cu, user=cls.cu_mem_user)
        cls.hkust_member = Member.objects.create(uid='resmem3', name='Res Member HKUST', university=cls.hkust, user=cls.hkust_mem_user)

        # Create Accommodations
        cls.acc1_hku_only = Accommodation.objects.create(
            type='studio', address='8 University Drive, Pok Fu Lam', owner=cls.owner,
            flat_number='S1', floor_number='1S',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=1, bedrooms=1, daily_price='120.00'
            )
        cls.acc1_hku_only.available_at_universities.add(cls.hku)
        cls.acc1_hku_only.update_geocoding() # Call geocoding after creation

        cls.acc2_hku_cu = Accommodation.objects.create(
            type='apartment', address='12 Science Park Road, Sha Tin', owner=cls.owner,
            flat_number='A2', floor_number='2A',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=2, bedrooms=1, daily_price='180.00'
            )
        cls.acc2_hku_cu.available_at_universities.add(cls.hku, cls.cu)
        cls.acc2_hku_cu.update_geocoding() # Call geocoding after creation

        cls.acc3_all_unis = Accommodation.objects.create(
            type='shared', address='9 Clear Water Bay Road, Sai Kung', owner=cls.owner,
            flat_number='SH3', floor_number='3S',
            available_from='2025-01-01', available_until='2025-12-31',
            beds=3, bedrooms=1, daily_price='160.00'
            )
        cls.acc3_all_unis.available_at_universities.add(cls.hku, cls.cu, cls.hkust)
        cls.acc3_all_unis.update_geocoding() # Call geocoding after creation

        # Create Reservations (with different statuses and universities)
        cls.res_hku_pending = Reservation.objects.create(
            member=cls.hku_member, accommodation=cls.acc1_hku_only, university=cls.hku,
            start_date='2025-11-01', end_date='2025-11-10', status='pending'
        )
        cls.res_cu_confirmed = Reservation.objects.create(
            member=cls.cu_member, accommodation=cls.acc2_hku_cu, university=cls.cu,
            start_date='2025-12-01', end_date='2025-12-15', status='confirmed'
        )
        cls.res_hkust_completed = Reservation.objects.create(
            member=cls.hkust_member, accommodation=cls.acc3_all_unis, university=cls.hkust,
            start_date='2025-08-01', end_date='2025-08-05', status='completed'
        )

        cls.res_hku_confirmed_for_cancel = Reservation.objects.create(
            member=cls.hku_member, accommodation=cls.acc3_all_unis, university=cls.hku,
            start_date='2026-01-01', end_date='2026-01-10', status='confirmed'
        )

    def _get_url(self, role_str, pk): # Helper for detail URL
        # Assumes router basename 'reservation'
        base_url = reverse('reservation-detail', kwargs={'pk': pk})
        return f"{base_url}?role={role_str}"

class ReservationMemberActionsTests(ReservationBaseTestCase):

    def test_member_can_cancel_own_pending_reservation(self):
        """Verify member can cancel their own PENDING reservation (DELETE)."""
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_url(role, self.res_hku_pending.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify the reservation status is now cancelled
        self.res_hku_pending.refresh_from_db()
        self.assertEqual(self.res_hku_pending.status, 'cancelled')
        # with self.assertRaises(Reservation.DoesNotExist):
        #     Reservation.objects.get(pk=self.res_hku_pending.id)

    def test_member_cannot_cancel_others_pending_reservation(self):
        """Verify member cannot cancel another member's pending reservation."""
        role = f"cu:member:{self.cu_member.uid}" # CU member
        url = self._get_url(role, self.res_hku_pending.id) # HKU member's reservation
        response = self.client.delete(url)

        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("cannot access reservations belonging to other users or universities", str(response.data).lower())
        # Ensure original reservation still exists and is unchanged
        self.assertTrue(Reservation.objects.filter(pk=self.res_hku_pending.id, status='pending').exists())

    def test_member_cannot_cancel_completed_reservation(self):
        """Verify member cannot cancel a COMPLETED reservation."""
        role = f"hkust:member:{self.hkust_member.uid}"
        url = self._get_url(role, self.res_hkust_completed.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Check the specific message from CanAccessReservationObject
        self.assertIn("cannot cancel reservations that are already completed", str(response.data).lower())
        self.assertTrue(Reservation.objects.filter(pk=self.res_hkust_completed.id).exists())

    def test_member_can_cancel_own_confirmed_reservation(self):
        """Verify member can cancel their own CONFIRMED reservation (DELETE)."""
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_url(role, self.res_hku_confirmed_for_cancel.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify the reservation status is now cancelled
        self.res_hku_confirmed_for_cancel.refresh_from_db()
        self.assertEqual(self.res_hku_confirmed_for_cancel.status, 'cancelled')
        # with self.assertRaises(Reservation.DoesNotExist):
        #     Reservation.objects.get(pk=self.res_hku_confirmed_for_cancel.id)

class ReservationSpecialistActionsTests(ReservationBaseTestCase):

    def test_specialist_can_cancel_own_uni_pending_reservation(self):
        """Verify specialist can cancel a PENDING reservation from their university."""
        role = f"hku:specialist:{self.hku_specialist.id}"
        url = self._get_url(role, self.res_hku_pending.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify the reservation status is now cancelled
        self.res_hku_pending.refresh_from_db()
        self.assertEqual(self.res_hku_pending.status, 'cancelled')
        # with self.assertRaises(Reservation.DoesNotExist):
        #     Reservation.objects.get(pk=self.res_hku_pending.id)

    def test_specialist_can_cancel_own_uni_confirmed_reservation(self):
        """Verify specialist can cancel a CONFIRMED reservation from their university."""
        role = f"cu:specialist:{self.cu_specialist.id}" # Now use the created CU specialist
        url = self._get_url(role, self.res_cu_confirmed.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify the reservation status is now cancelled
        self.res_cu_confirmed.refresh_from_db()
        self.assertEqual(self.res_cu_confirmed.status, 'cancelled')
        # with self.assertRaises(Reservation.DoesNotExist):
        #     Reservation.objects.get(pk=self.res_cu_confirmed.id)

    def test_specialist_cannot_cancel_other_uni_reservation(self):
        """Verify specialist cannot cancel a reservation from another university."""
        role = f"hkust:specialist:{self.hkust_specialist.id}" # HKUST specialist
        url = self._get_url(role, self.res_hku_pending.id) # HKU reservation
        response = self.client.delete(url)
        
        # Should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("cannot access reservations belonging to other users or universities", str(response.data).lower())
        # Ensure original reservation still exists and is unchanged
        self.assertTrue(Reservation.objects.filter(pk=self.res_hku_pending.id, status='pending').exists())

    def test_specialist_cannot_cancel_completed_reservation(self):
        """Verify specialist cannot cancel a COMPLETED reservation."""
        role = f"hkust:specialist:{self.hkust_specialist.id}"
        url = self._get_url(role, self.res_hkust_completed.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Check the specific message from CanAccessReservationObject
        self.assertIn("cannot cancel reservations that are already completed", str(response.data).lower())
        self.assertTrue(Reservation.objects.filter(pk=self.res_hkust_completed.id).exists())


class ReservationNotificationTests(ReservationBaseTestCase):

    def test_notification_sent_on_new_reservation(self, mock_send_mail=None):
        """Verify email notification is sent to relevant specialists on new reservation creation."""
        # Clear the outbox before the action
        mail.outbox = []
        
        role = f"hku:member:{self.hku_member.uid}"
        # Assumes router basename 'reservation'
        url = reverse('reservation-list') # POST to list endpoint
        url_with_role = f"{url}?role={role}"
        data = {
            "accommodation": self.acc3_all_unis.id,
            "university": self.hku.code,
            "start_date": "2026-02-01",
            "end_date": "2026-02-10"
        }
        response = self.client.post(url_with_role, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Check the outbox
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(self.hku_specialist.user.email, email.to)
        self.assertIn("New Pending Reservation", email.subject)

    def test_notification_sent_on_specialist_cancel(self, mock_send_mail=None):
        """Verify email notification is sent to member on specialist cancellation."""
        mail.outbox = []
        role = f"hku:specialist:{self.hku_specialist.id}"
        url = self._get_url(role, self.res_hku_confirmed_for_cancel.id) 

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Check the outbox (expecting emails to member AND specialists)
        self.assertEqual(len(mail.outbox), 2) # Should be 2 emails sent (specialists + member)
        # Find the email to the member
        member_email = next((email for email in mail.outbox if self.hku_member.user.email in email.to), None)
        self.assertIsNotNone(member_email)
        self.assertEqual(member_email.to, [self.hku_member.user.email])
        self.assertIn("Reservation Cancelled", member_email.subject)
        # Optionally check specialist email too
        specialist_email = next((email for email in mail.outbox if self.hku_specialist.user.email in email.to), None)
        self.assertIsNotNone(specialist_email)

    def test_notification_sent_on_member_cancel(self, mock_send_mail=None):
        """Verify email notification is sent to specialists on member cancellation."""
        mail.outbox = []
        role = f"hku:member:{self.hku_member.uid}"
        # Target the specific reservation designed for cancellation tests
        url = self._get_url(role, self.res_hku_confirmed_for_cancel.id) 

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Check the outbox (expecting only email to specialists when member cancels)
        self.assertEqual(len(mail.outbox), 1) # Should be 1 email sent (to specialists)
        email = mail.outbox[0]
        # Verify it went to the specialist(s) and not the member
        self.assertIn(self.hku_specialist.user.email, email.to)
        self.assertNotIn(self.hku_member.user.email, email.to)
        self.assertIn("Reservation Cancelled", email.subject)
