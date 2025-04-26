"""
Notification utilities for the UniHaven application.

This module provides functionality for sending notifications to users,
particularly for reservation-related events.
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)

def send_reservation_confirmation(reservation):
    """
    Send a confirmation email for a new reservation to both the student and specialist.
    """
    try:
        subject = f"UniHaven Reservation Confirmation #{reservation.id}"
        message = f"""
Dear {reservation.member.name},

Your reservation has been confirmed with the following details:

Reservation ID: {reservation.id}
Accommodation: {reservation.accommodation.address}
Type: {reservation.accommodation.type}
Check-in: {reservation.start_date}
Check-out: {reservation.end_date}
Status: {reservation.status}

You can view or cancel this reservation through your account.

Regards,
The UniHaven Team
        """
        recipient_email = f"{reservation.member.uid}@connect.hku.hk"
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'unihaven@example.com',
            [recipient_email],
            fail_silently=False,
        )
        logger.info(f"Reservation confirmation sent for reservation #{reservation.id}")
        
        specialist = reservation.accommodation.specialist
        if specialist:
            specialist_email = (
                specialist.user.email if specialist.user and specialist.user.email
                else "cedars-specialist@example.com" 
            )
        specialist_subject = f"New Reservation Created: #{reservation.id}"
        specialist_message = f"""
Dear specialist,

A new reservation has been created for an accommodation you manage:

Reservation ID: {reservation.id}
Accommodation: {reservation.accommodation.address}
Type: {reservation.accommodation.type}
Check-in: {reservation.start_date}
Check-out: {reservation.end_date}
Status: {reservation.status}

Regards,
The UniHaven Team
        """
        send_specialist_notification(reservation, specialist_subject, specialist_message)
        return True

    except Exception as e:
        logger.error(f"Failed to send reservation confirmation: {str(e)}")
        return False

def send_reservation_update(reservation, old_status):
    """
    Send a notification when a reservation status changes to both the student and the specialist.
    """
    try:
        subject = f"UniHaven Reservation Update #{reservation.id}"
        message = f"""
Dear {reservation.member.name},

Your reservation status has been updated:

Reservation ID: {reservation.id}
Accommodation: {reservation.accommodation.address}
Previous Status: {old_status}
New Status: {reservation.status}

"""
        if reservation.status == 'cancelled':
            message += f"This reservation was cancelled by {reservation.cancelled_by}.\n"
        
        message += """
You can view your reservations through your account.

Regards,
The UniHaven Team
        """
        recipient_email = f"{reservation.member.uid}@connect.hku.hk"
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'unihaven@example.com',
            [recipient_email],
            fail_silently=False,
        )
        logger.info(f"Reservation update notification sent for reservation #{reservation.id}")
        
        specialist = reservation.accommodation.specialist
        if specialist:
            specialist_email = (
                specialist.user.email if specialist.user and specialist.user.email
                else "cedars-specialist@example.com"  # 默认邮箱地址
            )
        specialist_subject = f"Reservation Update: #{reservation.id}"
        specialist_message = f"""
Dear specialist,

The following reservation status has been updated:

Reservation ID: {reservation.id}
Accommodation: {reservation.accommodation.address}
Previous Status: {old_status}
New Status: {reservation.status}

"""
        if reservation.status == 'cancelled':
            specialist_message += f"This reservation was cancelled by {reservation.cancelled_by}.\n"
        
        specialist_message += """
Regards,
The UniHaven Team
        """
        send_specialist_notification(reservation, specialist_subject, specialist_message)
        return True

    except Exception as e:
        logger.error(f"Failed to send reservation update notification: {str(e)}")
        return False

def send_specialist_notification(reservation, subject, message):
    """
    Send a notification email to the CEDARS Specialist managing the accommodation.

    Args:
        reservation (Reservation): The Reservation object related to the notification.
        subject (str): The subject of the email.
        message (str): The message body of the email.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    try:
        specialist = reservation.accommodation.specialist
        # 确保默认邮箱逻辑被正确使用
        specialist_email = (
            specialist.user.email if specialist and specialist.user and specialist.user.email
            else "cedars-specialist@example.com"
        )
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'unihaven@example.com',
            [specialist_email], 
            fail_silently=False,
        )
        logger.info(f"Notification sent to CEDARS Specialist for reservation #{reservation.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to CEDARS Specialist: {str(e)}")
        return False

def send_reservation_notification(reservation, subject, message_template):
    """Sends notification emails to relevant specialists for a reservation."""
    # Import models here
    from ..models import Specialist
    
    university = reservation.university
    if not university:
        logger.error(f"Cannot send notification for Reservation #{reservation.id} because it has no linked university.")
        return

    recipient_emails = set()
    specialists = Specialist.objects.filter(university=university)
    logger.debug(f"[send_reservation_notification] Querying specialists for Uni ID: {university.id}. Found: {list(specialists.values_list('id', 'name'))}")

    if not specialists.exists():
        logger.warning(f"No specialists found for university {university.code} to notify about Reservation #{reservation.id}")

    for specialist in specialists:
        if specialist.user and specialist.user.email:
            recipient_emails.add(specialist.user.email)
        else:
            logger.warning(f"Specialist {specialist.id} ({specialist.name}) at {university.code} has no associated user or email.")

    if recipient_emails:
        message = message_template.format(
            id=reservation.id,
            member_name=reservation.member.name,
            member_uid=reservation.member.uid,
            accommodation=reservation.accommodation,
            start_date=reservation.start_date,
            end_date=reservation.end_date,
            status=reservation.status,
            cancelled_by=reservation.cancelled_by or 'N/A'
        )
        try:
            num_sent = send_mail(
                subject,
                message,
                None, 
                list(recipient_emails),
                fail_silently=False,
            )
            logger.info(f"Sent {num_sent} specialist notification emails for Reservation #{reservation.id} ({subject}).")
        except Exception as e:
             logger.error(f"Failed to send specialist notification emails for Reservation #{reservation.id}: {e}")
    else:
         logger.warning(f"No valid specialist emails found to send notification for Reservation #{reservation.id} for university: {university.code}")

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





