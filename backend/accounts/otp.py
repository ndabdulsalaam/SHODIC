"""OTP generation and email sending utilities."""

import random
import logging
import threading
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


def generate_otp():
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def _build_html_email(otp_code, purpose):
    """Build branded HTML email with RxChat styling."""
    if purpose == 'registration':
        heading = 'Welcome to RxChat!'
        intro = 'Your verification code is:'
        preheader = 'Use this code to verify your email address.'
        footer_note = "If you didn't request this, please ignore this email."
    elif purpose == 'password_reset':
        heading = 'Reset Your Password'
        intro = 'Your password reset code is:'
        preheader = 'Use this code to reset your RxChat password.'
        footer_note = "If you didn't request a password reset, please ignore this email."
    elif purpose == 'email_change':
        heading = 'Verify Your New Email'
        intro = 'You requested to add this email to your RxChat account. Your verification code is:'
        preheader = 'Use this code to verify your new email address.'
        footer_note = "If you didn't request this, please ignore this email."
    else:
        heading = 'Login Verification'
        intro = 'We noticed a login from a new device. Your verification code is:'
        preheader = 'We noticed a login from a new device. Your verification code is inside.'
        footer_note = "If this wasn't you, please consider changing your password."

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:#f0f2f5; font-family:'Inter',Arial,sans-serif;">
  <div style="display:none; max-height:0; overflow:hidden; opacity:0; color:transparent; mso-hide:all;">{preheader}</div>
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
    <tr><td align="center">
      <table width="420" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0d1b3e,#1a2d5a); padding:32px 40px; text-align:center;">
            <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
              <tr>
                <td style="padding-left:12px; font-size:24px; font-weight:700; color:#ffffff;">Rx<span style="color:#2ec4b6;">Chat</span></td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            <h1 style="margin:0 0 16px; font-size:22px; color:#0d1b3e;">{heading}</h1>
            <p style="margin:0 0 24px; font-size:15px; color:#4a5568; line-height:1.5;">{intro}</p>
            <div style="background:#f0f9f8; border:2px solid #2ec4b6; border-radius:12px; padding:20px; text-align:center; margin-bottom:24px;">
              <span style="font-size:36px; font-weight:700; letter-spacing:8px; color:#0d1b3e;">{otp_code}</span>
            </div>
            <p style="margin:0 0 8px; font-size:13px; color:#718096;">This code expires in <strong>5 minutes</strong>.</p>
            <p style="margin:0; font-size:13px; color:#a0aec0;">{footer_note}</p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f7fafc; padding:20px 40px; text-align:center; border-top:1px solid #e2e8f0;">
            <p style="margin:0; font-size:12px; color:#a0aec0;">© RxChat — Your trusted AI pharmacist</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _send_via_brevo(to_email, subject, plain_text, html_content):
    """Send email via Brevo HTTP API (never blocked by network firewalls)."""
    api_key = getattr(settings, 'BREVO_API_KEY', '')
    sender_email = getattr(settings, 'BREVO_SENDER_EMAIL', '')
    sender_name = getattr(settings, 'BREVO_SENDER_NAME', 'RxChat')

    headers = {
        'accept': 'application/json',
        'api-key': api_key,
        'content-type': 'application/json',
    }

    payload = {
        'sender': {'name': sender_name, 'email': sender_email},
        'to': [{'email': to_email}],
        'subject': subject,
        'htmlContent': html_content,
        'textContent': plain_text,
    }

    resp = requests.post(BREVO_API_URL, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    logger.info(f"OTP email sent to {to_email} via Brevo (messageId={resp.json().get('messageId')})")


def _send_via_django(to_email, subject, plain_text, html_content):
    """Fallback: send via Django's configured email backend (console in dev)."""
    from django.core.mail import EmailMultiAlternatives

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=False)
    logger.info(f"OTP email sent to {to_email} via Django backend")


def send_otp_email(email, otp_code, purpose='registration'):
    """Send branded HTML OTP email to user (non-blocking).

    Uses Brevo HTTP API if BREVO_API_KEY is set, otherwise falls back
    to Django's email backend (console in dev, SMTP in prod).
    """
    if purpose == 'registration':
        subject = 'Verify Your Email'
        plain = f"Use this code to verify your email address: {otp_code} (expires in 5 min)"
    elif purpose == 'password_reset':
        subject = 'Reset Your Password'
        plain = f"Use this code to reset your RxChat password: {otp_code} (expires in 5 min)"
    elif purpose == 'email_change':
        subject = 'Verify Your New Email'
        plain = f"Use this code to verify your new email address: {otp_code} (expires in 5 min)"
    else:
        subject = 'We noticed a login from a new device'
        plain = f"We noticed a login from a new device. Your verification code is {otp_code} (expires in 5 min)"

    html_content = _build_html_email(otp_code, purpose)

    use_brevo = bool(getattr(settings, 'BREVO_API_KEY', ''))

    def _send():
        try:
            if use_brevo:
                _send_via_brevo(email, subject, plain, html_content)
            else:
                _send_via_django(email, subject, plain, html_content)
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {e}")

    # Send in background thread so the HTTP response returns immediately
    threading.Thread(target=_send, daemon=True).start()
    return True
