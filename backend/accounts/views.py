import logging
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import (
    PendingRegistration, TrustedDevice, PendingLoginOTP, PasswordResetOTP,
    UserProfile, UserEmail, PendingEmailChange, ROLE_CHOICES, GENDER_CHOICES,
    AGE_RANGE_CHOICES,
)
from .otp import generate_otp, send_otp_email

logger = logging.getLogger(__name__)
VALID_ROLES = [choice[0] for choice in ROLE_CHOICES]
VALID_GENDERS = [choice[0] for choice in GENDER_CHOICES]
VALID_AGE_RANGES = [choice[0] for choice in AGE_RANGE_CHOICES]


def _get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')[:300]


def _get_device_token(request):
    return request.COOKIES.get('device_token')


def _is_trusted_device(user, request):
    """Check if the current device is trusted and active."""
    device_token = _get_device_token(request)
    if not device_token:
        logger.debug("No trusted-device cookie found for user_id=%s", user.id)
        return False
    
    try:
        device = TrustedDevice.objects.get(user=user, device_token=device_token)
    except TrustedDevice.DoesNotExist:
        logger.debug("Trusted-device token not found for user_id=%s", user.id)
        return False

    if not device.is_active():
        logger.debug("Trusted-device token expired for user_id=%s", user.id)
        device.delete()  # Clean up stale device
        return False

    logger.debug("Trusted device accepted for user_id=%s", user.id)
    return device


def _refresh_authenticated_session(request):
    """Keep active authenticated browser sessions and trusted devices alive."""
    if not request.user.is_authenticated:
        return

    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
    request.session.modified = True

    device_token = _get_device_token(request)
    if not device_token:
        return

    try:
        device = TrustedDevice.objects.get(
            user=request.user,
            device_token=device_token,
        )
    except TrustedDevice.DoesNotExist:
        return

    if device.is_active():
        device.touch()
    else:
        device.delete()


def _trust_device(user, request, response):
    """Create a trusted device entry and set the cookie."""
    user_agent = _get_user_agent(request)
    device, _created = TrustedDevice.objects.get_or_create(
        user=user,
        user_agent=user_agent,
    )
    # Always refresh last_used on trust
    device.last_used = timezone.now()
    device.save(update_fields=['last_used'])

    # Use settings-aware cookie parameters
    secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
    samesite = getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax')

    response.set_cookie(
        'device_token',
        str(device.device_token),
        max_age=TrustedDevice.TRUST_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite=samesite,
        secure=secure,
        path='/',
    )
    return response


def _validate_setup_fields(data, fallback_first_name='', fallback_last_name=''):
    """Validate and extract common profile-setup fields.

    Returns (fields_dict, error_response).  Exactly one will be None.
    """
    preferred_name = data.get('preferred_name', '').strip()
    first_name = data.get('first_name', '').strip() or fallback_first_name
    last_name = data.get('last_name', '').strip() or fallback_last_name
    gender = data.get('gender', '').strip().lower()
    age_range = data.get('age_range', '').strip()
    phone_number = data.get('phone_number', '').strip()
    role = data.get('role', '').strip().lower()
    password = data.get('password', '')

    if not preferred_name:
        return None, Response({'error': 'Please tell us what Rx should call you'}, status=status.HTTP_400_BAD_REQUEST)
    if not first_name:
        return None, Response({'error': 'First name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if role not in VALID_ROLES:
        return None, Response({'error': 'Please select a valid role'}, status=status.HTTP_400_BAD_REQUEST)
    if gender not in VALID_GENDERS:
        return None, Response({'error': 'Please select a valid gender'}, status=status.HTTP_400_BAD_REQUEST)
    if age_range not in VALID_AGE_RANGES:
        return None, Response({'error': 'Please select a valid age range'}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 8:
        return None, Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)

    return {
        'preferred_name': preferred_name,
        'first_name': first_name,
        'last_name': last_name,
        'gender': gender,
        'age_range': age_range,
        'phone_number': phone_number,
        'role': role,
        'password': password,
    }, None


def _create_user_with_profile(email, fields):
    """Create a User and populate their auto-created profile."""
    user = User.objects.create_user(
        username=email,
        email=email,
        password=fields['password'],
    )
    profile = user.profile
    profile.preferred_name = fields['preferred_name']
    profile.first_name = fields['first_name']
    profile.last_name = fields['last_name']
    profile.role = fields['role']
    profile.gender = fields['gender']
    profile.age_range = fields['age_range']
    profile.phone_number = fields['phone_number']
    profile.save()
    return user


def _user_response(user):
    profile = getattr(user, 'profile', None)
    return {
        'id': user.id,
        'email': user.email,
        'first_name': profile.first_name if profile else '',
        'last_name': profile.last_name if profile else '',
        'preferred_name': profile.preferred_name if profile else '',
        'role': profile.role if profile else 'patient',
        'gender': profile.gender if profile else '',
        'age_range': profile.age_range if profile else '',
        'phone_number': profile.phone_number if profile else '',
    }


def _find_user_by_email(email):
    """Find a user by email (case-insensitive)."""
    return User.objects.filter(email__iexact=email).first()


def _drop_stale_pending_registrations():
    PendingRegistration.objects.filter(expires_at__lt=timezone.now()).delete()


# ─── Registration Flow ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /auth/register/
    Body: { "email" }
    Sends OTP email. Does NOT create user yet.
    """
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(email__iexact=email).exists():
        return Response(
            {'error': 'An account with this email already exists'},
            status=status.HTTP_409_CONFLICT,
        )

    _drop_stale_pending_registrations()
    otp_code = generate_otp()

    # Upsert pending registration (handles resend)
    PendingRegistration.objects.filter(email=email).delete()
    PendingRegistration.objects.create(
        email=email,
        otp_code=otp_code,
    )

    send_otp_email(email, otp_code, purpose='registration')

    return Response({
        'message': 'OTP sent to your email',
        'email': email,
        'otp_required': True,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    POST /auth/verify-otp/
    Body: { "email": "...", "otp": "..." }
    Verifies OTP, stores verified email in session, returns setup_required.
    """
    email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()

    if not email or not otp:
        return Response(
            {'error': 'Email and OTP are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pending = PendingRegistration.objects.get(email=email)
    except PendingRegistration.DoesNotExist:
        return Response(
            {'error': 'No pending registration found. Please register again.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if pending.is_stale():
        pending.delete()
        return Response(
            {'error': 'Pending registration has expired. Please register again.'},
            status=status.HTTP_410_GONE,
        )

    if pending.is_expired():
        return Response(
            {'error': 'OTP has expired. Please register again.'},
            status=status.HTTP_410_GONE,
        )

    if pending.otp_code != otp:
        return Response(
            {'error': 'Invalid OTP code'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Email verified — store in session for complete_setup
    request.session['verified_email'] = email
    pending.delete()

    return Response({
        'message': 'Email verified! Complete your profile.',
        'email': email,
        'setup_required': True,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def complete_setup(request):
    """
    POST /auth/complete-setup/
    Body: { "preferred_name", "first_name", "last_name", "role", "password" }
    Creates account after email has been verified via OTP.
    """
    verified_email = request.session.get('verified_email')
    if not verified_email:
        return Response(
            {'error': 'No verified email found. Please verify your email first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    fields, error = _validate_setup_fields(request.data)
    if error:
        return error

    if User.objects.filter(email__iexact=verified_email).exists():
        del request.session['verified_email']
        return Response(
            {'error': 'An account with this email already exists'},
            status=status.HTTP_409_CONFLICT,
        )

    user = _create_user_with_profile(verified_email, fields)

    del request.session['verified_email']
    login(request, user)

    response = Response({
        **_user_response(user),
        'message': 'Account created successfully',
    }, status=status.HTTP_201_CREATED)

    return _trust_device(user, request, response)


# ─── Login Flow ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /auth/login/
    Body: { "identifier": "email or username", "password": "..." }
    If trusted device → logs in directly.
    If new device → sends OTP, returns otp_required.
    """
    email = request.data.get('email', '').strip().lower()
    # Fallback: also accept 'identifier' field for backwards compatibility
    if not email:
        email = request.data.get('identifier', '').strip().lower()
    password = request.data.get('password', '')

    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find user by email
    user = _find_user_by_email(email)
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Verify password
    if not user.check_password(password):
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Check if device is trusted (returns device object or False)
    device = _is_trusted_device(user, request)
    if device:
        device.touch()  # Refresh the 15-day window
        login(request, user)
        return Response(_user_response(user))

    # New device — send OTP
    otp_code = generate_otp()
    PendingLoginOTP.objects.filter(user=user).delete()
    PendingLoginOTP.objects.create(user=user, otp_code=otp_code)

    send_otp_email(user.email, otp_code, purpose='login')

    return Response({
        'message': 'OTP sent — verify your device',
        'email': user.email,
        'otp_required': True,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_device(request):
    """
    POST /auth/verify-device/
    Body: { "email": "...", "otp": "..." }
    Verifies OTP for login on a new device. Trusts the device.
    """
    email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        pending = PendingLoginOTP.objects.get(user=user)
    except PendingLoginOTP.DoesNotExist:
        return Response(
            {'error': 'No pending verification. Please login again.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if pending.is_expired():
        pending.delete()
        return Response(
            {'error': 'OTP has expired. Please login again.'},
            status=status.HTTP_410_GONE,
        )

    if pending.otp_code != otp:
        return Response(
            {'error': 'Invalid OTP code'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    pending.delete()
    login(request, user)

    response = Response({
        **_user_response(user),
        'message': 'Device verified and trusted',
    })

    return _trust_device(user, request, response)


# ─── Resend OTP ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    """
    POST /auth/resend-otp/
    Body: { "email": "...", "purpose": "registration" | "login" | "password_reset" }
    """
    email = request.data.get('email', '').strip().lower()
    purpose = request.data.get('purpose', 'registration')

    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    _drop_stale_pending_registrations()
    otp_code = generate_otp()

    if purpose == 'registration':
        try:
            pending = PendingRegistration.objects.get(email=email)
            pending.otp_code = otp_code
            pending.otp_expires_at = timezone.now() + timedelta(minutes=PendingRegistration.OTP_MINUTES)
            pending.save(update_fields=['otp_code', 'otp_expires_at'])
        except PendingRegistration.DoesNotExist:
            return Response(
                {'error': 'No pending registration found'},
                status=status.HTTP_404_NOT_FOUND,
            )
    elif purpose == 'password_reset':
        user = _find_user_by_email(email)
        if user is None:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        PasswordResetOTP.objects.filter(user=user).delete()
        PasswordResetOTP.objects.create(user=user, otp_code=otp_code)
    else:
        # Purpose: login / device verification
        user = _find_user_by_email(email)
        if user is None:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        PendingLoginOTP.objects.filter(user=user).delete()
        PendingLoginOTP.objects.create(user=user, otp_code=otp_code)

    send_otp_email(email, otp_code, purpose=purpose)

    return Response({'message': 'OTP resent successfully'})


# ─── Forgot Password ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    POST /auth/forgot-password/
    Body: { "email": "email or username" }
    Sends OTP to reset password.
    """
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Look up by email
    user = _find_user_by_email(email)
    if user is None:
        return Response(
            {'error': 'No account found for this email'},
            status=status.HTTP_404_NOT_FOUND,
        )

    otp_code = generate_otp()
    PasswordResetOTP.objects.filter(user=user).delete()
    PasswordResetOTP.objects.create(user=user, otp_code=otp_code)

    send_otp_email(user.email, otp_code, purpose='password_reset')

    return Response({
        'message': 'Password reset code sent to your email',
        'email': user.email,
        'otp_required': True,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_reset_otp(request):
    """
    POST /auth/verify-reset-otp/
    Body: { "email": "...", "otp": "..." }
    Verifies OTP for password reset. Returns a token to confirm the reset.
    """
    email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid request'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pending = PasswordResetOTP.objects.get(user=user)
    except PasswordResetOTP.DoesNotExist:
        return Response(
            {'error': 'No reset request found. Please try again.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if pending.is_expired():
        pending.delete()
        return Response(
            {'error': 'OTP has expired. Please request a new code.'},
            status=status.HTTP_410_GONE,
        )

    if pending.otp_code != otp:
        return Response(
            {'error': 'Invalid OTP code'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Mark as verified so reset_password can proceed
    pending.verified = True
    pending.save()

    return Response({'message': 'OTP verified. You can now set a new password.', 'verified': True})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    POST /auth/reset-password/
    Body: { "email": "...", "password": "..." }
    Sets new password after OTP has been verified.
    """
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    if not email or not password:
        return Response(
            {'error': 'Email and new password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response(
            {'error': 'Invalid request'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Ensure OTP was verified
    try:
        pending = PasswordResetOTP.objects.get(user=user, verified=True)
    except PasswordResetOTP.DoesNotExist:
        return Response(
            {'error': 'OTP not verified. Please verify your code first.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    user.set_password(password)
    user.save()
    pending.delete()

    return Response({'message': 'Password updated successfully'})


# ─── Session ───

@csrf_exempt
@api_view(['POST'])
def logout_view(request):
    """POST /auth/logout/"""
    logout(request)
    return Response({'message': 'Logged out'})


@csrf_exempt
@api_view(['GET'])
def me(request):
    """GET /auth/me/"""
    if request.user.is_authenticated:
        _refresh_authenticated_session(request)
        return Response(_user_response(request.user))
    return Response({'user': None})


# ─── Profile Update ───

@csrf_exempt
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    PATCH /auth/profile/
    Body: any of { "first_name", "last_name", "preferred_name", "role", "gender", "age_range", "phone_number" }
    Updates profile fields for the authenticated user.
    """
    profile = request.user.profile

    allowed_fields = ['first_name', 'last_name', 'preferred_name', 'role', 'gender', 'age_range', 'phone_number']
    updated = []

    for field in allowed_fields:
        value = request.data.get(field)
        if value is not None:
            value = value.strip()
            if field == 'role' and value not in VALID_ROLES:
                return Response(
                    {'error': 'Please select a valid role'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if field == 'gender' and value not in VALID_GENDERS:
                return Response(
                    {'error': 'Please select a valid gender'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if field == 'age_range' and value not in VALID_AGE_RANGES:
                return Response(
                    {'error': 'Please select a valid age range'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            setattr(profile, field, value)
            updated.append(field)

    if not updated:
        return Response(
            {'error': 'No fields to update'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile.save()
    return Response({
        **_user_response(request.user),
        'message': 'Profile updated successfully',
    })


# ─── Email Management ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_email(request):
    """
    POST /auth/email/add/
    Body: { "email": "new@example.com" }
    Sends OTP to the new email for verification.
    """

    new_email = request.data.get('email', '').strip().lower()

    if not new_email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if email is already in use by another user
    if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
        return Response(
            {'error': 'This email is already in use'},
            status=status.HTTP_409_CONFLICT,
        )

    if UserEmail.objects.filter(email__iexact=new_email).exists():
        return Response(
            {'error': 'This email is already associated with an account'},
            status=status.HTTP_409_CONFLICT,
        )

    # Generate OTP and store pending change
    otp_code = generate_otp()
    PendingEmailChange.objects.filter(user=request.user).delete()
    PendingEmailChange.objects.create(
        user=request.user,
        new_email=new_email,
        otp_code=otp_code,
    )

    send_otp_email(new_email, otp_code, purpose='email_change')

    return Response({
        'message': 'Verification code sent to your new email',
        'email': new_email,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_email(request):
    """
    POST /auth/email/verify/
    Body: { "email": "new@example.com", "otp": "123456" }
    Verifies the OTP, adds the email as verified, and sets it as primary.
    """
    new_email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()

    if not new_email or not otp:
        return Response(
            {'error': 'Email and OTP are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        pending = PendingEmailChange.objects.get(user=request.user, new_email=new_email)
    except PendingEmailChange.DoesNotExist:
        return Response(
            {'error': 'No pending email change found. Please add the email first.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if pending.is_expired():
        pending.delete()
        return Response(
            {'error': 'Verification code has expired. Please try again.'},
            status=status.HTTP_410_GONE,
        )

    if pending.otp_code != otp:
        return Response(
            {'error': 'Invalid verification code'},
            status=status.HTTP_400_BAD_REQUEST,
        )


    # Unset current primary
    UserEmail.objects.filter(user=request.user, is_primary=True).update(is_primary=False)

    # Create the verified email record and set as primary
    user_email, _created = UserEmail.objects.get_or_create(
        user=request.user,
        email=new_email,
        defaults={'is_verified': True, 'is_primary': True, 'verified_at': timezone.now()},
    )
    if not _created:
        user_email.is_verified = True
        user_email.is_primary = True
        user_email.verified_at = timezone.now()
        user_email.save()

    # Update the Django User.email to the new primary
    request.user.email = new_email
    request.user.username = new_email
    request.user.save()

    pending.delete()

    return Response({
        **_user_response(request.user),
        'message': 'Email verified and set as primary',
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_email(request):
    """
    POST /auth/email/remove/
    Body: { "email": "old@example.com" }
    Removes a verified email — blocked if it's the only verified email.
    """
    email_to_remove = request.data.get('email', '').strip().lower()

    if not email_to_remove:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_email = UserEmail.objects.get(user=request.user, email__iexact=email_to_remove)
    except UserEmail.DoesNotExist:
        return Response(
            {'error': 'Email not found on your account'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if user_email.is_primary:
        return Response(
            {'error': 'Cannot remove your primary email. Set another email as primary first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Ensure at least one verified email remains
    verified_count = UserEmail.objects.filter(user=request.user, is_verified=True).count()
    if verified_count <= 1 and user_email.is_verified:
        return Response(
            {'error': 'You must have at least one verified email. Add and verify a new email first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_email.delete()

    return Response({'message': 'Email removed successfully'})





# ─── Google OAuth ───

import requests as http_requests
from urllib.parse import urlencode, urlparse
from django.shortcuts import redirect


GOOGLE_CALLBACK_PATH = '/auth/google/callback/'


def _is_local_host(host):
    parsed_host = urlparse(f"//{host or ''}").hostname
    hostname = (parsed_host or host or '').strip('[]').lower()
    return hostname in {'localhost', '127.0.0.1', '::1'}


def _is_local_url(url):
    return _is_local_host(urlparse(url or '').netloc)


def _origin_from_url(url):
    parsed = urlparse(url or '')
    if not parsed.scheme or not parsed.netloc:
        return ''
    return f'{parsed.scheme}://{parsed.netloc}'


def _allowed_frontend_origins():
    return [
        origin.rstrip('/')
        for origin in getattr(settings, 'ALLOWED_ORIGINS', [])
        if origin.startswith(('http://', 'https://'))
    ]


def _request_frontend_origin(request):
    allowed_origins = set(_allowed_frontend_origins())
    requested_origin = _origin_from_url(request.query_params.get('return_origin'))
    if requested_origin in allowed_origins:
        return requested_origin

    for header in ('HTTP_ORIGIN', 'HTTP_REFERER'):
        origin = _origin_from_url(request.META.get(header))
        if origin in allowed_origins:
            return origin
    return ''


def _google_frontend_url_for_request(request):
    request_origin = _request_frontend_origin(request)
    if request_origin:
        return request_origin

    allowed_origins = _allowed_frontend_origins()
    if settings.DEBUG:
        local_origin = next((origin for origin in allowed_origins if _is_local_url(origin)), '')
        if local_origin:
            return local_origin

    remote_origin = next((origin for origin in allowed_origins if not _is_local_url(origin)), '')
    if remote_origin:
        return remote_origin

    return request.build_absolute_uri('/').rstrip('/')


def _google_auth_mode_for_request(request):
    auth_mode = request.query_params.get('auth_mode', '').strip().lower()
    return auth_mode if auth_mode in {'login', 'signup'} else 'login'


def _google_redirect_uri_for_request(request):
    return request.build_absolute_uri(GOOGLE_CALLBACK_PATH)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def google_login(request):
    """GET /auth/google/login/ — Redirect to Google consent screen."""
    redirect_uri = _google_redirect_uri_for_request(request)
    request.session['google_redirect_uri'] = redirect_uri
    request.session['google_frontend_url'] = _google_frontend_url_for_request(request)
    request.session['google_auth_mode'] = _google_auth_mode_for_request(request)

    params = urlencode({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'select_account',
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def google_callback(request):
    """
    GET /auth/google/callback/?code=...
    Exchanges code for tokens, fetches profile, finds/creates user.
    New Google users are redirected to a setup page to pick username + password.
    """
    code = request.query_params.get('code')
    error = request.query_params.get('error')
    frontend = request.session.get('google_frontend_url') or _google_frontend_url_for_request(request)
    redirect_uri = request.session.get('google_redirect_uri') or _google_redirect_uri_for_request(request)

    if error or not code:
        return redirect(f'{frontend}/?auth_error=google_denied')

    # Exchange code for tokens
    try:
        token_resp = http_requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        token_data = token_resp.json()
        access_token = token_data.get('access_token')
        if not access_token:
            return redirect(f'{frontend}/?auth_error=token_failed')
    except Exception:
        return redirect(f'{frontend}/?auth_error=token_failed')

    # Fetch user profile
    try:
        profile_resp = http_requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        profile = profile_resp.json()
        google_email = profile.get('email', '').lower()
        google_first = profile.get('given_name', '')
        google_last = profile.get('family_name', '')
        if not google_email:
            return redirect(f'{frontend}/?auth_error=no_email')
    except Exception:
        return redirect(f'{frontend}/?auth_error=profile_failed')

    # Find or create user
    # Find existing non-staff user with this email
    user = User.objects.filter(email__iexact=google_email).first()

    if user:
        # Existing user — log in directly
        login(request, user)
        request.session.pop('google_redirect_uri', None)
        request.session.pop('google_frontend_url', None)
        request.session.pop('google_auth_mode', None)
        resp = redirect(frontend)
        resp = _trust_device(user, request, resp)
        return resp
    else:
        # New user — store Google profile in session, redirect to setup page
        request.session['google_pending'] = {
            'email': google_email,
            'first_name': google_first,
            'last_name': google_last,
        }
        request.session.pop('google_redirect_uri', None)
        request.session.pop('google_frontend_url', None)
        request.session.pop('google_auth_mode', None)
        return redirect(f'{frontend}/auth?step=google_setup')


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def google_pending_profile(request):
    """GET /auth/google/pending-profile/ — return pending Google signup data."""
    pending = request.session.get('google_pending')
    if not pending:
        return Response(
            {'error': 'No pending Google sign-up. Please try again.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response({
        'email': pending.get('email', ''),
        'first_name': pending.get('first_name', ''),
        'last_name': pending.get('last_name', ''),
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def google_complete_setup(request):
    """
    POST /auth/google/complete-setup/
    Body: { "preferred_name", "first_name", "last_name", "role", "password" }
    Creates account for a new Google user.
    """
    pending = request.session.get('google_pending')
    if not pending:
        return Response(
            {'error': 'No pending Google sign-up. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    google_email = pending.get('email', '')
    fallback_first = pending.get('first_name') or google_email.split('@')[0]
    fallback_last = pending.get('last_name', '')

    fields, error = _validate_setup_fields(
        request.data,
        fallback_first_name=fallback_first,
        fallback_last_name=fallback_last,
    )
    if error:
        return error

    user = _create_user_with_profile(google_email, fields)

    del request.session['google_pending']
    login(request, user)

    response = Response({
        **_user_response(user),
        'message': 'Account created successfully',
    }, status=status.HTTP_201_CREATED)
    return _trust_device(user, request, response)
