from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import University, PropertyOwner, Member, Specialist, Accommodation, Reservation
from unittest.mock import patch
from datetime import date, timedelta

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
            available_from='2025-10-01', available_until='2025-12-31',
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
            available_from='2025-01-01', available_until='2026-06-30',
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

    def test_member_can_cancel_own_pending_reservation_via_patch(self):
        """Verify member can cancel their own PENDING reservation via PATCH."""
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_url(role, self.res_hku_pending.id)
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.res_hku_pending.refresh_from_db()
        self.assertEqual(self.res_hku_pending.status, 'cancelled')
        self.assertEqual(self.res_hku_pending.cancelled_by, 'member') # Check who cancelled

    def test_member_cannot_cancel_others_pending_reservation_via_patch(self):
        """Verify member cannot cancel another member's pending reservation via PATCH."""
        role = f"cu:member:{self.cu_member.uid}" # CU member
        url = self._get_url(role, self.res_hku_pending.id) # HKU member's reservation
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("cannot access reservations belonging to other users or universities", str(response.data).lower())
        self.assertTrue(Reservation.objects.filter(pk=self.res_hku_pending.id, status='pending').exists())

    def test_member_cannot_cancel_completed_reservation_via_patch(self):
        """Verify member cannot cancel a COMPLETED reservation via PATCH."""
        role = f"hkust:member:{self.hkust_member.uid}"
        url = self._get_url(role, self.res_hkust_completed.id)
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        # Check if the expected error message is in the list of errors for the 'status' field
        self.assertIn("cannot change status from 'completed'.", response.data['status'])
        # Verify the reservation status hasn't changed
        self.res_hkust_completed.refresh_from_db()
        self.assertEqual(self.res_hkust_completed.status, 'completed')

    def test_member_cannot_cancel_own_confirmed_reservation_via_patch(self):
        """Verify member cannot cancel their own CONFIRMED reservation via PATCH."""
        role = f"hku:member:{self.hku_member.uid}"
        url = self._get_url(role, self.res_hku_confirmed_for_cancel.id)
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        # Expect 400 due to validation in perform_update checking old_status != 'pending' for members
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("members can only cancel reservations that are currently pending", str(response.data).lower())
        self.assertTrue(Reservation.objects.filter(pk=self.res_hku_confirmed_for_cancel.id, status='confirmed').exists())

    def test_create_reservation(self):
        """Verify member can create a new reservation (POST)."""
        role = f"hku:member:{self.hku_member.uid}"
        url = reverse('reservation-list')
        url_with_role = f"{url}?role={role}"
        # Use different, valid dates for self.acc1 to avoid overlap with setUpTestData
        data = {
            'accommodation': self.acc1_hku_only.id,
            'start_date': date(2025, 12, 1).strftime('%Y-%m-%d'), 
            'end_date': date(2025, 12, 10).strftime('%Y-%m-%d'),
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Role {role}')
        response = self.client.post(url_with_role, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Verify the reservation is created
        reservation = Reservation.objects.get(pk=response.data['id'])
        self.assertEqual(reservation.member, self.hku_member)
        self.assertEqual(reservation.accommodation, self.acc1_hku_only)
        self.assertEqual(reservation.university, self.hku)
        self.assertEqual(reservation.status, 'pending')  # Default status for new reservations
        self.assertEqual(response.data['start_date'], data['start_date'])
        self.assertEqual(response.data['end_date'], data['end_date'])
        self.assertEqual(reservation.start_date.strftime('%Y-%m-%d'), data['start_date'])
        self.assertEqual(reservation.end_date.strftime('%Y-%m-%d'), data['end_date'])
        self.assertEqual(len(mail.outbox), 2)
        # Check Specialist Email
        email = mail.outbox[0]
        self.assertIn(self.hku_specialist.user.email, email.to)
        self.assertIn("New Pending Reservation", email.subject)
        # Check Member Email
        member_email = mail.outbox[1]
        self.assertIn(self.hku_member.user.email, member_email.to)
        self.assertIn("Reservation Received", member_email.subject)

    def test_list_reservations(self):
        """Verify member can list their own reservations (GET)."""
        role = f"hku:member:{self.hku_member.uid}"
        url = reverse('reservation-list') + f"?role={role}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Direct list access, no pagination
        self.assertIsInstance(response.data, list) 
        results = response.data 
        reservation_ids = {res['id'] for res in results}

        # Check expected reservations are present
        self.assertIn(self.res_hku_pending.id, reservation_ids)
        self.assertIn(self.res_hku_confirmed_for_cancel.id, reservation_ids)
        # Check unexpected reservations are absent
        self.assertNotIn(self.res_cu_confirmed.id, reservation_ids)
        self.assertNotIn(self.res_hkust_completed.id, reservation_ids)
        # Check the count
        self.assertEqual(len(results), 2)

        # Check statuses individually without assuming order
        statuses = {res['id']: res['status'] for res in results}
        self.assertEqual(statuses.get(self.res_hku_pending.id), 'pending')
        self.assertEqual(statuses.get(self.res_hku_confirmed_for_cancel.id), 'confirmed')

    def test_create_reservation_fails_overlap(self):
        """Verify creating a reservation fails if it overlaps with an existing one for the same accommodation."""
        role = f"hku:member:{self.hku_member.uid}"
        url = reverse('reservation-list') + f"?role={role}"
        # Dates overlapping with self.res_hku_pending (2025-11-01 to 2025-11-10)
        data = {
            'accommodation': self.acc1_hku_only.id,
            'start_date': date(2025, 11, 5).strftime('%Y-%m-%d'), # Overlaps 
            'end_date': date(2025, 11, 15).strftime('%Y-%m-%d'),  # Within availability, but overlaps res
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check for the specific overlap error message from the serializer
        self.assertIn("existing reservation", str(response.data).lower())

    def test_create_reservation_fails_outside_availability(self):
        """Verify creating a reservation fails if dates are outside accommodation availability."""
        role = f"hku:member:{self.hku_member.uid}"
        url = reverse('reservation-list') + f"?role={role}"
        # Ensure we have date objects for calculations
        acc1_available_from = self.acc1_hku_only.available_from
        acc1_available_until = self.acc1_hku_only.available_until
        # Convert if they are not already date objects (DateField should return date objects)
        if isinstance(acc1_available_from, str):
            acc1_available_from = date.fromisoformat(acc1_available_from)
        if isinstance(acc1_available_until, str):
            acc1_available_until = date.fromisoformat(acc1_available_until)

        # 1. Test start date before accommodation available_from
        data_early = {
            'accommodation': self.acc1_hku_only.id,
            'start_date': (acc1_available_from - timedelta(days=5)).strftime('%Y-%m-%d'), 
            'end_date': (acc1_available_from + timedelta(days=5)).strftime('%Y-%m-%d'), 
        }
        response_early = self.client.post(url, data_early, format='json')
        self.assertEqual(response_early.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start_date", response_early.data)
        self.assertIn(f"not available until {acc1_available_from}", str(response_early.data['start_date']).lower())

        # 2. Test end date after accommodation available_until
        data_late = {
            'accommodation': self.acc1_hku_only.id,
            'start_date': (acc1_available_until - timedelta(days=5)).strftime('%Y-%m-%d'), 
            'end_date': (acc1_available_until + timedelta(days=5)).strftime('%Y-%m-%d'),
        }
        response_late = self.client.post(url, data_late, format='json')
        self.assertEqual(response_late.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("end_date", response_late.data)
        self.assertIn(f"only available until {acc1_available_until}", str(response_late.data['end_date']).lower())

class ReservationSpecialistActionsTests(ReservationBaseTestCase):

    def test_specialist_can_cancel_own_uni_pending_reservation_via_patch(self):
        """Verify specialist can cancel a PENDING reservation via PATCH."""
        role = f"hku:specialist:{self.hku_specialist.id}"
        url = self._get_url(role, self.res_hku_pending.id)
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.res_hku_pending.refresh_from_db()
        self.assertEqual(self.res_hku_pending.status, 'cancelled')
        self.assertEqual(self.res_hku_pending.cancelled_by, 'specialist') # Check who cancelled

    def test_specialist_can_cancel_own_uni_confirmed_reservation_via_patch(self):
        """Verify specialist can cancel a CONFIRMED reservation via PATCH."""
        role = f"cu:specialist:{self.cu_specialist.id}" 
        url = self._get_url(role, self.res_cu_confirmed.id)
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.res_cu_confirmed.refresh_from_db()
        self.assertEqual(self.res_cu_confirmed.status, 'cancelled')
        self.assertEqual(self.res_cu_confirmed.cancelled_by, 'specialist') # Check who cancelled

    def test_specialist_cannot_cancel_other_uni_reservation_via_patch(self):
        """Verify specialist cannot cancel a reservation from another uni via PATCH."""
        role = f"hkust:specialist:{self.hkust_specialist.id}" # HKUST specialist
        url = self._get_url(role, self.res_hku_pending.id) # HKU reservation
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("cannot access reservations belonging to other users or universities", str(response.data).lower())
        self.assertTrue(Reservation.objects.filter(pk=self.res_hku_pending.id, status='pending').exists())

    def test_specialist_cannot_cancel_completed_reservation_via_patch(self):
        """Verify specialist cannot cancel a COMPLETED reservation via PATCH."""
        role = f"hkust:specialist:{self.hkust_specialist.id}"
        url = self._get_url(role, self.res_hkust_completed.id)
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        # Check if the expected error message is in the list of errors for the 'status' field
        self.assertIn("cannot change status from 'completed'.", response.data['status'])
        # Verify the reservation status hasn't changed
        self.res_hkust_completed.refresh_from_db()
        self.assertEqual(self.res_hkust_completed.status, 'completed')

    def test_delete_reservation_disallowed(self):
        """Verify DELETE method is disallowed for reservations."""
        role = f"hku:specialist:{self.hku_specialist.id}"
        url = self._get_url(role, self.res_hku_pending.id)
        response = self.client.delete(url)
        # Expect 403 Forbidden because permissions block before the 405 override is reached
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class ReservationNotificationTests(ReservationBaseTestCase):

    # Mock mail.outbox for notification tests
    def setUp(self):
        mail.outbox = []

    def test_notification_sent_on_new_reservation(self):
        """Verify email notification is sent to relevant specialists on new reservation creation."""
        role = f"hku:member:{self.hku_member.uid}"
        url = reverse('reservation-list') + f"?role={role}"
        data = {
            "accommodation": self.acc3_all_unis.id,
            "university": self.hku.code, # University code is not needed in request body
            "start_date": "2026-02-01",
            "end_date": "2026-02-10"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 2) # Updated: Expect 2 emails (Specialist + Member)
        email = mail.outbox[0]
        self.assertIn(self.hku_specialist.user.email, email.to)
        self.assertIn("New Pending Reservation", email.subject)
        # Check member email too
        member_email = mail.outbox[1]
        self.assertIn(self.hku_member.user.email, member_email.to)
        self.assertIn("Reservation Received", member_email.subject)

    def test_notification_sent_on_specialist_cancel(self):
        """Verify email notification is sent to member on specialist cancellation via PATCH."""
        role = f"hku:specialist:{self.hku_specialist.id}"
        url = self._get_url(role, self.res_hku_confirmed_for_cancel.id)
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json') # Use PATCH

        self.assertEqual(response.status_code, status.HTTP_200_OK) # Expect 200
        self.assertEqual(len(mail.outbox), 2) # Expect 2 emails (specialist + member)
        # Find the email to the member
        member_email = next((email for email in mail.outbox if self.hku_member.user.email in email.to), None)
        self.assertIsNotNone(member_email)
        self.assertEqual(member_email.to, [self.hku_member.user.email])
        self.assertIn("Reservation Cancelled", member_email.subject)
        # Optionally check specialist email too
        specialist_email = next((email for email in mail.outbox if self.hku_specialist.user.email in email.to), None)
        self.assertIsNotNone(specialist_email)
        self.assertIn("Reservation Cancelled", specialist_email.subject)

    def test_notification_sent_on_member_cancel(self):
        """Verify email notification is sent to specialists on member cancellation via PATCH."""
        role = f"hku:member:{self.hku_member.uid}"
        # Use the PENDING reservation for member cancellation test
        url = self._get_url(role, self.res_hku_pending.id) 
        data = {'status': 'cancelled'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 2)
        # Check specialist email
        self.assertIn(self.hku_specialist.user.email, mail.outbox[0].to)
        self.assertIn(f"Reservation Cancelled at {self.hku.code}", mail.outbox[0].subject)
        # Check member email
        self.assertIn(self.hku_member.user.email, mail.outbox[1].to)
        self.assertIn(f"Reservation Cancelled: UniHaven Booking", mail.outbox[1].subject)
