import uuid
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


ROLE_CHOICES = [
    ('patient', 'Patient'),
    ('pharmacist', 'Pharmacist'),
    ('physician', 'Physician'),
    ('nurse', 'Nurse'),
    ('other_health_professional', 'Other Health Professional'),
]


class UserProfile(models.Model):
    """Extends Django User with identity and role for Audience-Aware Prompting."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    preferred_name = models.CharField(max_length=150, blank=True, help_text="What should Rx call you?")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='patient')

    def __str__(self):
        return f"{self.user.email} — {self.get_role_display()}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


class PendingRegistration(models.Model):
    """Stores pending email verification until OTP is confirmed."""
    email = models.EmailField(unique=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pending: {self.email}"


class TrustedDevice(models.Model):
    """Tracks devices that have been verified via OTP — no repeat OTP on login."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trusted_devices')
    device_token = models.UUIDField(default=uuid.uuid4, unique=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'user_agent']

    def __str__(self):
        return f"Device for {self.user.email} ({self.device_token})"


class PendingLoginOTP(models.Model):
    """Stores OTP for login verification on new devices."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Login OTP for {self.user.email}"


class PasswordResetOTP(models.Model):
    """Stores OTP for password reset via email."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Password reset OTP for {self.user.email}"
