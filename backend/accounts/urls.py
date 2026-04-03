from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify-otp'),
    path('login/', views.login_view, name='login'),
    path('verify-device/', views.verify_device, name='verify-device'),
    path('resend-otp/', views.resend_otp, name='resend-otp'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify-reset-otp'),
    path('reset-password/', views.reset_password, name='reset-password'),
    path('google/login/', views.google_login, name='google-login'),
    path('google/callback/', views.google_callback, name='google-callback'),
    path('google/complete-setup/', views.google_complete_setup, name='google-complete-setup'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.me, name='me'),
    path('check-username/', views.check_username, name='check-username'),
]
