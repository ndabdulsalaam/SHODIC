from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from rest_framework.test import APIClient

from .models import PendingLoginOTP, PendingRegistration
from .otp import generate_otp


class OtpUtilityTests(TestCase):
    def test_generate_otp_returns_zero_padded_six_digit_code(self):
        with patch("accounts.otp.secrets.randbelow", return_value=42):
            self.assertEqual(generate_otp(), "000042")


class ProfileApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="profile@example.com",
            email="profile@example.com",
            password="password123",
        )

    def test_update_profile_updates_names_and_role(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Ada",
                "last_name": "Okafor",
                "preferred_name": "Dr Ada",
                "role": "pharmacist",
                "gender": "female",
                "age_range": "25_34",
                "phone_number": "+2348012345678",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.first_name, "Ada")
        self.assertEqual(self.user.profile.last_name, "Okafor")
        self.assertEqual(self.user.profile.preferred_name, "Dr Ada")
        self.assertEqual(self.user.profile.role, "pharmacist")
        self.assertEqual(self.user.profile.gender, "female")
        self.assertEqual(self.user.profile.age_range, "25_34")
        self.assertEqual(self.user.profile.phone_number, "+2348012345678")
        self.assertEqual(response.data["role"], "pharmacist")
        self.assertEqual(response.data["gender"], "female")

    def test_update_profile_rejects_invalid_role(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/api/auth/profile/",
            {"role": "wizard"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.role, "patient")


class AuthOtpFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="trusted@example.com",
            email="trusted@example.com",
            password="password123",
        )

    @patch("accounts.views.send_otp_email")
    def test_trusted_device_does_not_request_otp_on_second_or_third_visit(self, send_otp_email):
        first_login = self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": "password123"},
            format="json",
            HTTP_USER_AGENT="trusted-browser",
        )
        self.assertEqual(first_login.status_code, 200)
        self.assertTrue(first_login.data["otp_required"])
        send_otp_email.assert_called_once()

        pending = PendingLoginOTP.objects.get(user=self.user)
        verify = self.client.post(
            "/api/auth/verify-device/",
            {"email": self.user.email, "otp": pending.otp_code},
            format="json",
            HTTP_USER_AGENT="trusted-browser",
        )
        self.assertEqual(verify.status_code, 200)
        self.assertIn("device_token", self.client.cookies)

        self.client.post("/api/auth/logout/", format="json")
        second_login = self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": "password123"},
            format="json",
            HTTP_USER_AGENT="trusted-browser",
        )
        self.assertEqual(second_login.status_code, 200)
        self.assertNotIn("otp_required", second_login.data)

        self.client.post("/api/auth/logout/", format="json")
        third_login = self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": "password123"},
            format="json",
            HTTP_USER_AGENT="trusted-browser",
        )
        self.assertEqual(third_login.status_code, 200)
        self.assertNotIn("otp_required", third_login.data)
        self.assertEqual(send_otp_email.call_count, 1)

    @patch("accounts.views.send_otp_email")
    @patch("accounts.views.generate_otp", return_value="123456")
    def test_pending_registration_keeps_email_after_otp_expires(self, generate_otp, send_otp_email):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "pending@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        pending = PendingRegistration.objects.get(email="pending@example.com")
        pending.otp_expires_at = timezone.now() - timedelta(minutes=1)
        pending.save(update_fields=["otp_expires_at"])

        verify = self.client.post(
            "/api/auth/verify-otp/",
            {"email": "pending@example.com", "otp": "123456"},
            format="json",
        )

        self.assertEqual(verify.status_code, 410)
        self.assertTrue(PendingRegistration.objects.filter(email="pending@example.com").exists())

        resend = self.client.post(
            "/api/auth/resend-otp/",
            {"email": "pending@example.com", "purpose": "registration"},
            format="json",
        )
        self.assertEqual(resend.status_code, 200)
        pending.refresh_from_db()
        self.assertGreater(pending.otp_expires_at, timezone.now())
        self.assertGreater(pending.expires_at, timezone.now() + timedelta(days=29))

    def test_pending_registration_is_dropped_after_one_month(self):
        old_pending = PendingRegistration.objects.create(
            email="old-pending@example.com",
            otp_code="123456",
            otp_expires_at=timezone.now() - timedelta(days=31),
            expires_at=timezone.now() - timedelta(days=1),
        )

        response = self.client.post(
            "/api/auth/verify-otp/",
            {"email": old_pending.email, "otp": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 410)
        self.assertFalse(PendingRegistration.objects.filter(email=old_pending.email).exists())
