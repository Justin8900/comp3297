"""
Notification utilities for the UniHaven application.

This module provides functionality for sending notifications to users,
particularly for reservation-related events.
"""

import logging
from django.core.mail import send_mail
from django.conf import settings

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





