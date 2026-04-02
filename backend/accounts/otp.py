"""OTP generation and email sending utilities."""

import random
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))


def _build_html_email(otp_code, purpose):
    """Build branded HTML email with RxChat styling."""
    if purpose == 'registration':
        heading = 'Welcome to RxChat!'
        intro = 'Your verification code is:'
        footer_note = "If you didn't request this, please ignore this email."
    elif purpose == 'password_reset':
        heading = 'Reset Your Password'
        intro = 'Your password reset code is:'
        footer_note = "If you didn't request a password reset, please ignore this email."
    else:
        heading = 'Login Verification'
        intro = 'We noticed a login from a new device. Your verification code is:'
        footer_note = "If this wasn't you, please consider changing your password."

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; background:#f0f2f5; font-family:'Inter',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 20px;">
    <tr><td align="center">
      <table width="420" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0d1b3e,#1a2d5a); padding:32px 40px; text-align:center;">
            <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
              <tr>
                <td style="background:linear-gradient(135deg,#2ec4b6,#a8e6cf); width:40px; height:40px; border-radius:10px; text-align:center; vertical-align:middle; font-weight:700; font-size:18px; color:#0d1b3e;">Rx</td>
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
            <p style="margin:0 0 8px; font-size:13px; color:#718096;">This code expires in <strong>15 minutes</strong>.</p>
            <p style="margin:0; font-size:13px; color:#a0aec0;">{footer_note}</p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f7fafc; padding:20px 40px; text-align:center; border-top:1px solid #e2e8f0;">
            <p style="margin:0; font-size:12px; color:#a0aec0;">© RxChat — Your trusted AI pharmacy companion</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_otp_email(email, otp_code, purpose='registration'):
    """Send branded HTML OTP email to user."""
    if purpose == 'registration':
        subject = 'RxChat — Verify Your Email'
        plain = f"Welcome to RxChat! Your code: {otp_code} (expires in 15 min)"
    elif purpose == 'password_reset':
        subject = 'RxChat — Reset Your Password'
        plain = f"Your password reset code: {otp_code} (expires in 15 min)"
    else:
        subject = 'RxChat — Login Verification'
        plain = f"Login from new device. Your code: {otp_code} (expires in 15 min)"

    html_content = _build_html_email(otp_code, purpose)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)
        logger.info(f"OTP email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False
