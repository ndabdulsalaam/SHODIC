from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import PendingRegistration, TrustedDevice, PendingLoginOTP, PasswordResetOTP, UserProfile


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
    list_display = ['email', 'created_at', 'expires_at']
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
    list_display = ['first_name', 'last_name', 'preferred_name', 'email', 'role']
    search_fields = ['user__email', 'first_name', 'last_name', 'preferred_name']
    list_filter = ['role']

    @admin.display(description='Email')
    def email(self, obj):
        return obj.user.email
