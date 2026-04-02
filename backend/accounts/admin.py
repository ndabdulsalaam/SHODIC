from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import PendingRegistration, TrustedDevice, PendingLoginOTP, PasswordResetOTP


# Unregister default, re-register with customizations
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']


@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'first_name', 'last_name', 'created_at', 'expires_at']
    search_fields = ['email', 'username']


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_token', 'created_at']
    search_fields = ['user__email', 'user__username']


@admin.register(PendingLoginOTP)
class PendingLoginOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at']
    search_fields = ['user__email', 'user__username']


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'verified', 'created_at', 'expires_at']
    search_fields = ['user__email', 'user__username']
