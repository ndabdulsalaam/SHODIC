from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify-otp'),
    path('complete-setup/', views.complete_setup, name='complete-setup'),
    path('login/', views.login_view, name='login'),
    path('verify-device/', views.verify_device, name='verify-device'),
    path('resend-otp/', views.resend_otp, name='resend-otp'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify-reset-otp'),
    path('reset-password/', views.reset_password, name='reset-password'),
    path('google/login/', views.google_login, name='google-login'),
    path('google/callback/', views.google_callback, name='google-callback'),
    path('google/pending-profile/', views.google_pending_profile, name='google-pending-profile'),
    path('google/complete-setup/', views.google_complete_setup, name='google-complete-setup'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.me, name='me'),
    # Profile & Email management
    path('profile/', views.update_profile, name='update-profile'),
    path('email/add/', views.add_email, name='add-email'),
    path('email/verify/', views.verify_email, name='verify-email'),
    path('email/remove/', views.remove_email, name='remove-email'),
]
