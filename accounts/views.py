
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import RegisterSerializer, UserProfileSerializer, UpdateProfileSerializer
from .models import UserProfile

UserModel = get_user_model()

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        identifier = attrs.get('username')
        user = UserModel.objects.filter(email=identifier).first() or UserModel.objects.filter(username=identifier).first()
        if user:
            attrs['username'] = user.username
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['email'] = self.user.email
        # Add admin status to token response
        data['is_staff'] = self.user.is_staff
        data['is_superuser'] = self.user.is_superuser
        # Add profile IDs to token response for frontend use
        try:
            profile = self.user.userprofile
            data['user_faculty_id'] = profile.faculty_id
            data['user_department_id'] = profile.department_id
            data['user_level_id'] = profile.level_id
            data['user_course_area_id'] = profile.course_area_id
        except UserProfile.DoesNotExist:
            pass # Handle cases where profile might not exist
        return data

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Manually trigger the token creation to include profile data
            refresh = MyTokenObtainPairSerializer.get_token(user)
            data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
            # Add user and profile info to the registration response
            data.update(MyTokenObtainPairSerializer(context=self.get_serializer_context()).validate(request.data))
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def get_serializer_context(self):
        return {'request': self.request}


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.userprofile
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            profile = request.user.userprofile
            serializer = UpdateProfileSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Return the updated profile
                updated_serializer = UserProfileSerializer(profile)
                return Response(updated_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)


class IsAdminUser(APIView):
    """Permission class to check if user is admin."""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class UserListView(APIView):
    """
    List all users (admin only).
    Returns basic user info for admin management panel.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only allow admin users
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        users = UserModel.objects.all().select_related('userprofile')
        user_list = []
        
        for user in users:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
            
            # Add profile info if exists
            try:
                profile = user.userprofile
                user_data['faculty'] = profile.faculty.name if profile.faculty else None
                user_data['department'] = profile.department.name if profile.department else None
                user_data['level'] = profile.level.name if profile.level else None
            except UserProfile.DoesNotExist:
                pass
            
            user_list.append(user_data)
        
        return Response({
            'count': len(user_list),
            'users': user_list
        })


class UserDetailView(APIView):
    """
    Update user admin status (admin only).
    PATCH to toggle is_staff field.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        # Only allow admin users
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = UserModel.objects.get(id=user_id)
        except UserModel.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prevent self-demotion
        if user.id == request.user.id:
            return Response(
                {'error': 'Cannot modify your own admin status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update is_staff if provided
        if 'is_staff' in request.data:
            user.is_staff = request.data['is_staff']
            user.save()
        
        return Response({
            'id': user.id,
            'username': user.username,
            'is_staff': user.is_staff,
            'message': 'User updated successfully'
        })

