from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-otp/', views.verify_otp, name='verify-otp'),
    path('login/', views.login_view, name='login'),
    path('verify-device/', views.verify_device, name='verify-device'),
    path('resend-otp/', views.resend_otp, name='resend-otp'),
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.me, name='me'),
]
