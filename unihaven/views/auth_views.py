"""
Authentication views for the UniHaven application.

This module provides views for user authentication, including login and logout.
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from ..models import HKUMember, CEDARSSpecialist, PropertyOwner

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Authenticate a user and return an auth token.
    
    Args:
        request (Request): The HTTP request containing username and password
        
    Returns:
        Response: Authentication token and user details or error message
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Please provide both username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Get or create token
    token, _ = Token.objects.get_or_create(user=user)
    
    # Determine user role
    user_role = None
    user_id = None
    
    if hasattr(user, 'hkumember'):
        user_role = 'hku_member'
        user_id = user.hkumember.uid
    elif hasattr(user, 'cedarsspecialist'):
        user_role = 'cedars_specialist'
        user_id = user.cedarsspecialist.id
    elif hasattr(user, 'propertyowner'):
        user_role = 'property_owner'
        user_id = user.propertyowner.id
    
    # Return token and user info
    return Response({
        'token': token.key,
        'user_id': user_id,
        'user_role': user_role,
        'username': user.username,
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Log out a user by deleting their auth token.
    
    Args:
        request (Request): The HTTP request
        
    Returns:
        Response: Success message
    """
    request.user.auth_token.delete()
    logout(request)
    
    return Response(
        {'success': 'Successfully logged out'},
        status=status.HTTP_200_OK
    ) 