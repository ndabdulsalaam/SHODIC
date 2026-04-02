"""OTP generation and email sending utilities."""

import random
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp_code, purpose='registration'):
    """Send OTP email to user."""
    if purpose == 'registration':
        subject = 'RxChat — Verify Your Email'
        message = f"""Welcome to RxChat!

Your verification code is: {otp_code}

Enter this code to complete your registration.
This code expires in 10 minutes.

If you didn't request this, please ignore this email.

— RxChat Team"""
    else:
        subject = 'RxChat — Login Verification'
        message = f"""Hi there,

We noticed a login from a new device. Your verification code is: {otp_code}

Enter this code to continue.
This code expires in 10 minutes.

If this wasn't you, please change your password immediately.

— RxChat Team"""

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False
