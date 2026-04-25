from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


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
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.first_name, "Ada")
        self.assertEqual(self.user.profile.last_name, "Okafor")
        self.assertEqual(self.user.profile.preferred_name, "Dr Ada")
        self.assertEqual(self.user.profile.role, "pharmacist")
        self.assertEqual(response.data["role"], "pharmacist")

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
