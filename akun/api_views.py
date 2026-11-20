from django.contrib.auth import login, logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Profile
from .serializers import (
    AccountRemovalSerializer,
    LoginSerializer,
    ProfileSerializer,
    PublicProfileSerializer,
    RegisterSerializer,
)
from .views import own_profile


@api_view(['GET', 'HEAD'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def csrf_token(request):
    return Response({'csrfToken': get_token(request._request)})


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
@transaction.atomic
def register(request):
    # SessionAuthentication only checks CSRF for authenticated requests by
    # default. Registration and login also need protection for anonymous users.
    SessionAuthentication().enforce_csrf(request)
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    profile = ProfileSerializer(own_profile(user), context={'request': request})
    return Response(profile.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def login_user(request):
    SessionAuthentication().enforce_csrf(request)
    serializer = LoginSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    login(request._request, serializer.user)
    profile = ProfileSerializer(own_profile(serializer.user), context={'request': request})
    return Response(profile.data)


@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def logout_user(request):
    logout(request._request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'HEAD', 'PUT', 'PATCH', 'DELETE'])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def profile_me(request):
    profile = own_profile(request.user)
    if request.method in ('GET', 'HEAD'):
        return Response(ProfileSerializer(profile, context={'request': request}).data)

    if request.method == 'DELETE':
        serializer = AccountRemovalSerializer(data=request.data, context={'profile': profile})
        serializer.is_valid(raise_exception=True)
        request.user.delete()
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = ProfileSerializer(
        profile, data=request.data, partial=request.method == 'PATCH',
        context={'request': request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['GET', 'HEAD'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def profile_detail(request, user_id):
    profile = get_object_or_404(
        Profile.objects.select_related('user'), user_id=user_id, user__is_active=True,
    )
    serializer = PublicProfileSerializer(profile, context={'request': request})
    return Response(serializer.data)
