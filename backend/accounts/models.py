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
    """Auto-create a UserProfile and primary UserEmail when a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)
        if instance.email:
            UserEmail.objects.get_or_create(
                user=instance,
                email=instance.email,
                defaults={'is_verified': True, 'is_primary': True, 'verified_at': timezone.now()},
            )


class UserEmail(models.Model):
    """Track multiple emails per user with verification status."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emails')
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'email']

    def __str__(self):
        flags = []
        if self.is_primary:
            flags.append('primary')
        if self.is_verified:
            flags.append('verified')
        return f"{self.email} ({', '.join(flags) or 'unverified'})"


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
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pending: {self.email}"


class PendingEmailChange(models.Model):
    """Stores OTP for verifying a new email address added to an account."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    new_email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Email change for {self.user.email} → {self.new_email}"


class TrustedDevice(models.Model):
    """Tracks devices that have been verified via OTP — no repeat OTP on login."""
    TRUST_DAYS = 15  # Re-require OTP after 15 days of inactivity

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trusted_devices')
    device_token = models.UUIDField(default=uuid.uuid4, unique=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'user_agent']

    def is_active(self):
        """Device is trusted only if used within the last TRUST_DAYS days."""
        return (timezone.now() - self.last_used) < timedelta(days=self.TRUST_DAYS)

    def touch(self):
        """Update last_used timestamp."""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])

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
            self.expires_at = timezone.now() + timedelta(minutes=5)
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
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Password reset OTP for {self.user.email}"


# ─── Subscription & Organization Models ───

class SubscriptionPlan(models.Model):
    """Available subscription tiers."""
    TIER_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('plus', 'Plus'),
        ('enterprise', 'Enterprise'),
    ]
    name = models.CharField(max_length=50, unique=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_messages_per_day = models.IntegerField(default=50, help_text='0 = unlimited')
    max_conversations = models.IntegerField(default=10, help_text='0 = unlimited')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price_monthly']

    def __str__(self):
        return f"{self.name} (₦{self.price_monthly}/mo)"


class Subscription(models.Model):
    """A user's active subscription."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('trialing', 'Trialing'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} — {self.plan.name} ({self.status})"


class Organization(models.Model):
    """A workspace for team/enterprise users."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name='owned_organizations')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    max_members = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.name} ({self.slug})"


class OrganizationMember(models.Model):
    """Membership linking users to organizations with roles."""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='org_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invitations_sent')

    class Meta:
        unique_together = ['organization', 'user']

    def __str__(self):
        return f"{self.user.email} — {self.get_role_display()} @ {self.organization.name}"
