import uuid
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import (
    PendingRegistration, TrustedDevice, PendingLoginOTP, PasswordResetOTP,
    UserProfile, UserEmail, PendingEmailChange, ROLE_CHOICES,
)
from .otp import generate_otp, send_otp_email

VALID_ROLES = [choice[0] for choice in ROLE_CHOICES]


def _get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')[:300]


def _get_device_token(request):
    return request.COOKIES.get('device_token')


def _is_trusted_device(user, request):
    """Check if the current device is trusted for this user."""
    device_token = _get_device_token(request)
    if not device_token:
        return False
    return TrustedDevice.objects.filter(
        user=user,
        device_token=device_token,
    ).exists()


def _trust_device(user, request, response):
    """Create a trusted device entry and set the cookie."""
    user_agent = _get_user_agent(request)
    device, _created = TrustedDevice.objects.get_or_create(
        user=user,
        user_agent=user_agent,
    )
    response.set_cookie(
        'device_token',
        str(device.device_token),
        max_age=365 * 24 * 60 * 60,  # 1 year
        httponly=True,
        samesite='Lax',
    )
    return response


def _user_response(user):
    profile = getattr(user, 'profile', None)
    return {
        'id': user.id,
        'email': user.email,
        'first_name': profile.first_name if profile else '',
        'last_name': profile.last_name if profile else '',
        'preferred_name': profile.preferred_name if profile else '',
        'role': profile.role if profile else 'patient',
    }


def _find_user_by_email(email):
    """Find a user by email (case-insensitive)."""
    return User.objects.filter(email__iexact=email).first()


# ─── Registration Flow ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register/
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
    POST /api/auth/verify-otp/
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

    if pending.is_expired():
        pending.delete()
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
    POST /api/auth/complete-setup/
    Body: { "preferred_name", "first_name", "last_name", "role", "password" }
    Creates account after email has been verified via OTP.
    """
    verified_email = request.session.get('verified_email')
    if not verified_email:
        return Response(
            {'error': 'No verified email found. Please verify your email first.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    preferred_name = request.data.get('preferred_name', '').strip()
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()
    role = request.data.get('role', '').strip().lower()
    password = request.data.get('password', '')

    if not preferred_name:
        return Response(
            {'error': 'Please tell us what Rx should call you'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not first_name:
        return Response(
            {'error': 'First name is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if role not in VALID_ROLES:
        return Response(
            {'error': 'Please select a valid role'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check email not already taken (edge case: someone registered between OTP and setup)
    if User.objects.filter(email__iexact=verified_email).exists():
        del request.session['verified_email']
        return Response(
            {'error': 'An account with this email already exists'},
            status=status.HTTP_409_CONFLICT,
        )

    # Create user — username auto-set to email
    user = User.objects.create_user(
        username=verified_email,
        email=verified_email,
        password=password,
    )
    # Update profile (auto-created via signal)
    profile = user.profile
    profile.preferred_name = preferred_name
    profile.first_name = first_name
    profile.last_name = last_name
    profile.role = role
    profile.save()

    # Clean up session
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
    POST /api/auth/login/
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

    # Check if device is trusted
    if _is_trusted_device(user, request):
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
    POST /api/auth/verify-device/
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
    POST /api/auth/resend-otp/
    Body: { "email": "...", "purpose": "registration" | "login" | "password_reset" }
    """
    email = request.data.get('email', '').strip().lower()
    purpose = request.data.get('purpose', 'registration')

    if not email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp_code = generate_otp()

    if purpose == 'registration':
        try:
            pending = PendingRegistration.objects.get(email=email)
            pending.otp_code = otp_code
            from django.utils import timezone
            from datetime import timedelta
            pending.expires_at = timezone.now() + timedelta(minutes=15)
            pending.save()
        except PendingRegistration.DoesNotExist:
            return Response(
                {'error': 'No pending registration found'},
                status=status.HTTP_404_NOT_FOUND,
            )
    elif purpose == 'password_reset':
        try:
            user = User.objects.get(email__iexact=email)
            PasswordResetOTP.objects.filter(user=user).delete()
            PasswordResetOTP.objects.create(user=user, otp_code=otp_code)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        try:
            user = User.objects.get(email__iexact=email, is_staff=False)
            PendingLoginOTP.objects.filter(user=user).delete()
            PendingLoginOTP.objects.create(user=user, otp_code=otp_code)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

    send_otp_email(email, otp_code, purpose=purpose)

    return Response({'message': 'OTP resent successfully'})


# ─── Forgot Password ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    POST /api/auth/forgot-password/
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
    POST /api/auth/verify-reset-otp/
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
    POST /api/auth/reset-password/
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
    """POST /api/auth/logout/"""
    logout(request)
    return Response({'message': 'Logged out'})


@csrf_exempt
@api_view(['GET'])
def me(request):
    """GET /api/auth/me/"""
    if request.user.is_authenticated:
        return Response(_user_response(request.user))
    return Response({'user': None})


# ─── Profile Update ───

@csrf_exempt
@api_view(['PATCH'])
def update_profile(request):
    """
    PATCH /api/auth/profile/
    Body: any of { "first_name", "last_name", "preferred_name", "role" }
    Updates profile fields for the authenticated user.
    """
    profile = request.user.profile

    allowed_fields = ['first_name', 'last_name', 'preferred_name', 'role']
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
def add_email(request):
    """
    POST /api/auth/email/add/
    Body: { "email": "new@example.com" }
    Sends OTP to the new email for verification.
    """
    from django.contrib.auth.models import User as UserModel

    new_email = request.data.get('email', '').strip().lower()

    if not new_email:
        return Response(
            {'error': 'Email is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if email is already in use by another user
    if UserModel.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
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
def verify_email(request):
    """
    POST /api/auth/email/verify/
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

    from django.utils import timezone as tz

    # Unset current primary
    UserEmail.objects.filter(user=request.user, is_primary=True).update(is_primary=False)

    # Create the verified email record and set as primary
    user_email, _created = UserEmail.objects.get_or_create(
        user=request.user,
        email=new_email,
        defaults={'is_verified': True, 'is_primary': True, 'verified_at': tz.now()},
    )
    if not _created:
        user_email.is_verified = True
        user_email.is_primary = True
        user_email.verified_at = tz.now()
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
def remove_email(request):
    """
    POST /api/auth/email/remove/
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
from urllib.parse import urlencode
from django.shortcuts import redirect
from django.conf import settings


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def google_login(request):
    """GET /api/auth/google/login/ — Redirect to Google consent screen."""
    params = urlencode({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
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
    GET /api/auth/google/callback/?code=...
    Exchanges code for tokens, fetches profile, finds/creates user.
    New Google users are redirected to a setup page to pick username + password.
    """
    code = request.query_params.get('code')
    error = request.query_params.get('error')
    frontend = settings.FRONTEND_URL

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
                'redirect_uri': settings.GOOGLE_REDIRECT_URI,
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
        return redirect(f'{frontend}/auth?step=google_setup')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def google_complete_setup(request):
    """
    POST /api/auth/google/complete-setup/
    Body: { "preferred_name", "first_name", "last_name", "role", "password" }
    Creates account for a new Google user.
    """
    pending = request.session.get('google_pending')
    if not pending:
        return Response(
            {'error': 'No pending Google sign-up. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    preferred_name = request.data.get('preferred_name', '').strip()
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()
    role = request.data.get('role', '').strip().lower()
    password = request.data.get('password', '')

    if not preferred_name:
        return Response(
            {'error': 'Please tell us what Rx should call you'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not first_name:
        return Response(
            {'error': 'First name is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if role not in VALID_ROLES:
        return Response(
            {'error': 'Please select a valid role'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    google_email = pending['email']

    # Create user — username auto-set to email
    user = User.objects.create_user(
        username=google_email,
        email=google_email,
        password=password,
    )
    # Update profile (auto-created via signal)
    profile = user.profile
    profile.preferred_name = preferred_name
    profile.first_name = first_name or pending.get('first_name', '')
    profile.last_name = last_name or pending.get('last_name', '')
    profile.role = role
    profile.save()

    # Clean up session
    del request.session['google_pending']

    login(request, user)
    resp_data = {
        **_user_response(user),
        'message': 'Account created successfully',
    }
    response = Response(resp_data, status=status.HTTP_201_CREATED)
    return response

