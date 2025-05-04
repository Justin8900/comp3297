"""
Notification utilities for the UniHaven application.

This module provides functionality for sending notifications to users,
particularly for reservation-related events.
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from ..models import Specialist

logger = logging.getLogger(__name__)

# --- Internal Helper for Sending to Specialists --- 
def _send_to_specialists(reservation, subject, message_template):
    """Internal helper to find specialists and send email."""
    university = reservation.university
    if not university:
        logger.error(f"Cannot send specialist notification for Reservation #{reservation.id} because it has no linked university.")
        return

    recipient_emails = set()
    specialists = Specialist.objects.filter(university=university)
    if not specialists.exists():
        logger.warning(f"No specialists found for university {university.code} to notify about Reservation #{reservation.id}")
        return # No recipients

    for specialist in specialists:
        if specialist.user and specialist.user.email:
            recipient_emails.add(specialist.user.email)
        else:
            logger.warning(f"Specialist {specialist.id} ({specialist.name}) at {university.code} has no associated user or email.")

    if not recipient_emails:
        logger.warning(f"No valid specialist emails found to send notification for Reservation #{reservation.id} for university: {university.code}")
        return # No recipients

    # Ensure all needed context is available for formatting
    context = {
        'id': reservation.id,
        'member_name': reservation.member.name if reservation.member else 'N/A',
        'member_uid': reservation.member.uid if reservation.member else 'N/A',
        'accommodation': reservation.accommodation, # Assumes __str__ is useful
        'start_date': reservation.start_date,
        'end_date': reservation.end_date,
        'status': reservation.status,
        'cancelled_by': reservation.cancelled_by or 'N/A',
        # Add any other fields needed by specific templates below
        'university_code': university.code
    }

    message = message_template.format(**context)
    
    try:
        num_sent = send_mail(
            subject.format(**context), # Allow subject formatting too
            message,
            None, # Use default sender
            list(recipient_emails),
            fail_silently=False,
        )
        logger.info(f"Sent {num_sent} specialist notification emails for Reservation #{reservation.id} ({subject.format(**context)}).")
    except Exception as e:
         logger.error(f"Failed to send specialist notification emails for Reservation #{reservation.id}: {e}")

# --- Specific Specialist Notification Functions --- 

def notify_specialists_of_creation(reservation):
    """Notifies specialists of a new pending reservation."""
    subject = "New Pending Reservation at {university_code}: #{id}"
    message_template = f"""
A new reservation requires confirmation:

Reservation ID: {{id}}
Member: {{member_name}} ({{member_uid}})
Accommodation: {{accommodation}}
Check-in: {{start_date}}
Check-out: {{end_date}}
Status: {{status}}

Please review and confirm or cancel this reservation.

Regards,
The UniHaven Team
    """
    _send_to_specialists(reservation, subject, message_template)

def notify_specialists_of_cancellation(reservation):
    """Notifies specialists of a cancelled reservation."""
    subject = "Reservation Cancelled at {university_code}: #{id}"
    message_template = f"""
The following reservation has been cancelled:

Reservation ID: {{id}}
Accommodation: {{accommodation}}
Member: {{member_name}} ({{member_uid}})
Cancelled by: {{cancelled_by}}

Regards,
The UniHaven Team
    """
    _send_to_specialists(reservation, subject, message_template)

def notify_specialists_of_update(reservation, new_status):
    """Notifies specialists of a status update (e.g., confirmed, completed)."""
    subject = f"Reservation Status Updated to {new_status.capitalize()} at {{university_code}}: #{{id}}"
    message_template = f"""
The following reservation status has been updated to {new_status}:

Reservation ID: {{id}}
Accommodation: {{accommodation}}
Member: {{member_name}} ({{member_uid}})
Check-in: {{start_date}}
Check-out: {{end_date}}
New Status: {{status}} # Note: reservation.status already holds the new status

Regards,
The UniHaven Team
    """
    _send_to_specialists(reservation, subject, message_template)

# --- Member Notification Functions --- (Keep as they are)

def send_member_cancellation_notification(reservation):
    """Sends a cancellation notification email to the member."""
    # Import models here
    from ..models import Member
    
    member = reservation.member
    if not member or not hasattr(member, 'user') or not member.user or not member.user.email:
        logger.warning(f"Cannot send cancellation email to member for Reservation #{reservation.id}: Member or associated user/email missing.")
        return
        
    subject = f"Reservation Cancelled: UniHaven Booking #{reservation.id}"
    message = f"""
Dear {member.name},

Your reservation for {reservation.accommodation} from {reservation.start_date} to {reservation.end_date} has been cancelled.

Cancelled by: {reservation.cancelled_by}

If you did not request this cancellation, please contact the university specialist.

Regards,
The UniHaven Team
    """
    try:
        num_sent = send_mail(
            subject,
            message,
            None,
            [member.user.email],
            fail_silently=False,
        )
        logger.info(f"Sent cancellation email to member {member.uid} for Reservation #{reservation.id}.")
    except Exception as e:
        logger.error(f"Failed to send member cancellation email for Reservation #{reservation.id}: {e}")

def send_member_creation_notification(reservation):
    """Sends a pending confirmation email to the member upon creation."""
    # Import models here
    from ..models import Member

    member = reservation.member
    if not member or not hasattr(member, 'user') or not member.user or not member.user.email:
        logger.warning(f"Cannot send creation email to member for Reservation #{reservation.id}: Member or associated user/email missing.")
        return

    subject = f"Reservation Received: UniHaven Booking #{reservation.id}"
    message = f"""
Dear {member.name},

We have received your reservation request for {reservation.accommodation} from {reservation.start_date} to {reservation.end_date}.

Reservation ID: {reservation.id}
Status: {reservation.status}

A specialist will review your request shortly. You will receive another notification once it is confirmed or if there are any issues.

Regards,
The UniHaven Team
    """
    try:
        num_sent = send_mail(
            subject,
            message,
            None, # Use default sender
            [member.user.email],
            fail_silently=False,
        )
        logger.info(f"Sent creation confirmation email to member {member.uid} for Reservation #{reservation.id}.")
    except Exception as e:
        logger.error(f"Failed to send member creation confirmation email for Reservation #{reservation.id}: {e}")

def send_member_update_notification(reservation, old_status):
    """Sends a status update notification email to the member."""
    # Import models here
    from ..models import Member

    member = reservation.member
    if not member or not hasattr(member, 'user') or not member.user or not member.user.email:
        logger.warning(f"Cannot send update email to member for Reservation #{reservation.id}: Member or associated user/email missing.")
        return

    subject = f"Reservation Update: UniHaven Booking #{reservation.id}"
    message = f"""
Dear {member.name},

An update regarding your reservation for {reservation.accommodation}:

Reservation ID: {reservation.id}
Previous Status: {old_status}
New Status: {reservation.status}

Regards,
The UniHaven Team
    """
    try:
        num_sent = send_mail(
            subject,
            message,
            None, # Use default sender
            [member.user.email],
            fail_silently=False,
        )
        logger.info(f"Sent status update email to member {member.uid} for Reservation #{reservation.id}.")
    except Exception as e:
        logger.error(f"Failed to send member status update email for Reservation #{reservation.id}: {e}")





