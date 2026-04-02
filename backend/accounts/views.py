import uuid
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import PendingRegistration, TrustedDevice, PendingLoginOTP, PasswordResetOTP
from .otp import generate_otp, send_otp_email


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
    device = TrustedDevice.objects.create(
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
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def _find_user_by_identifier(identifier):
    """Find user by email or username (case-insensitive)."""
    return User.objects.filter(
        Q(email__iexact=identifier) | Q(username__iexact=identifier)
    ).first()


# ─── Registration Flow ───

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register/
    Body: { "email", "password", "username", "first_name", "last_name" }
    Sends OTP email. Does NOT create user yet.
    """
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')
    username = request.data.get('username', '').strip()
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()

    if not email or not password or not username:
        return Response(
            {'error': 'Email, username, and password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(password) < 8:
        return Response(
            {'error': 'Password must be at least 8 characters'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not all(c.isalnum() or c in '_-' for c in username):
        return Response(
            {'error': 'Username can only contain letters, numbers, hyphens, and underscores'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Case-insensitive username uniqueness
    if User.objects.filter(username__iexact=username).exists():
        return Response(
            {'error': 'This username is already taken'},
            status=status.HTTP_409_CONFLICT,
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
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=make_password(password),
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
    Verifies OTP, creates user, trusts device, logs in.
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

    # Create user
    user = User.objects.create(
        username=pending.username,
        email=email,
        password=pending.password,  # Already hashed
        first_name=pending.first_name,
        last_name=pending.last_name,
    )
    pending.delete()

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
    identifier = request.data.get('identifier', '').strip()
    # Fallback: also accept 'email' field for backwards compatibility
    if not identifier:
        identifier = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not identifier or not password:
        return Response(
            {'error': 'Email/username and password are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Find user by email or username (case-insensitive)
    user = _find_user_by_identifier(identifier)
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
            user = User.objects.get(email__iexact=email)
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
    identifier = request.data.get('email', '').strip()

    if not identifier:
        return Response(
            {'error': 'Email or username is required'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Look up by email or username
    user = _find_user_by_identifier(identifier)
    if user is None:
        return Response(
            {'error': 'No account found with that email or username'},
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


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def check_username(request):
    """GET /api/auth/check-username/?username=xxx"""
    username = request.query_params.get('username', '').strip()
    if not username or len(username) < 3:
        return Response({'available': False, 'error': 'Username must be at least 3 characters'})
    if not all(c.isalnum() or c in '_-' for c in username):
        return Response({'available': False, 'error': 'Only letters, numbers, hyphens, underscores'})
    # Case-insensitive check
    taken = User.objects.filter(username__iexact=username).exists()
    return Response({'available': not taken})
