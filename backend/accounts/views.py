from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    POST /api/auth/register/
    Body: { "email": "...", "password": "...", "name": "..." }
    """
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    name = request.data.get('name', '').strip()

    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'An account with this email already exists'},
            status=status.HTTP_409_CONFLICT
        )

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name,
    )

    login(request, user)

    return Response({
        'id': user.id,
        'email': user.email,
        'name': user.first_name,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /api/auth/login/
    Body: { "email": "...", "password": "..." }
    """
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response(
            {'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    login(request, user)

    return Response({
        'id': user.id,
        'email': user.email,
        'name': user.first_name,
    })


@api_view(['POST'])
def logout_view(request):
    """POST /api/auth/logout/"""
    logout(request)
    return Response({'message': 'Logged out'})


@api_view(['GET'])
def me(request):
    """
    GET /api/auth/me/
    Get current user info (or null if anonymous).
    """
    if request.user.is_authenticated:
        return Response({
            'id': request.user.id,
            'email': request.user.email,
            'name': request.user.first_name,
        })
    return Response({'user': None})
