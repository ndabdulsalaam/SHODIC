from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import (
    PendingRegistration, TrustedDevice, PendingLoginOTP, PasswordResetOTP,
    UserProfile, UserEmail, PendingEmailChange,
    SubscriptionPlan, Subscription, Organization, OrganizationMember,
)


# Unregister default, re-register with customizations
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']

    @admin.display(description='Role')
    def role(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.get_role_display() if profile else '—'


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ['email', 'created_at', 'otp_expires_at', 'expires_at']
    search_fields = ['email']


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_token', 'created_at']
    search_fields = ['user__email']


@admin.register(PendingLoginOTP)
class PendingLoginOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at']
    search_fields = ['user__email']


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'verified', 'created_at', 'expires_at']
    search_fields = ['user__email']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'preferred_name', 'email', 'role', 'gender', 'age_range']
    search_fields = ['user__email', 'first_name', 'last_name', 'preferred_name', 'phone_number']
    list_filter = ['role', 'gender', 'age_range']

    @admin.display(description='Email')
    def email(self, obj):
        return obj.user.email


@admin.register(UserEmail)
class UserEmailAdmin(admin.ModelAdmin):
    list_display = ['email', 'user', 'is_verified', 'is_primary', 'verified_at']
    search_fields = ['email', 'user__email']
    list_filter = ['is_verified', 'is_primary']


@admin.register(PendingEmailChange)
class PendingEmailChangeAdmin(admin.ModelAdmin):
    list_display = ['user', 'new_email', 'created_at', 'expires_at']
    search_fields = ['user__email', 'new_email']


# ─── Subscription & Organization ───

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'price_monthly', 'max_messages_per_day', 'max_conversations', 'is_active']
    list_filter = ['tier', 'is_active']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'started_at', 'expires_at']
    search_fields = ['user__email']
    list_filter = ['status', 'plan']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner', 'plan', 'max_members', 'created_at']
    search_fields = ['name', 'slug', 'owner__email']
    list_filter = ['plan']


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'joined_at']
    search_fields = ['user__email', 'organization__name']
    list_filter = ['role']
