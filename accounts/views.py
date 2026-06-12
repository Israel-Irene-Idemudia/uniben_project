
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
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
            data['points'] = profile.points
            data['phone'] = profile.phone
            data['network'] = profile.network
            data['student_id'] = profile.student_id
            data['matric_number'] = profile.matric_number
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
        
        # Search filter
        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            users = users.filter(Q(username__icontains=search) | Q(email__icontains=search))
            
        # Order by newest
        users = users.order_by('-date_joined')
        
        # Pagination / Limit
        page = request.query_params.get('page')
        page_size = request.query_params.get('page_size', '100')
        
        try:
            page_size = int(page_size)
        except ValueError:
            page_size = 100
            
        total_count = users.count()
        
        if page:
            try:
                page = int(page)
                if page < 1:
                    page = 1
            except ValueError:
                page = 1
            start = (page - 1) * page_size
            end = start + page_size
            users = users[start:end]
        else:
            # Fallback limit to avoid server crash (default 100)
            users = users[:page_size]
            
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
            'count': total_count,
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

    def delete(self, request, user_id):
        """Delete a user (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = UserModel.objects.get(id=user_id)
            # Prevent deleting yourself
            if user.id == request.user.id:
                return Response(
                    {'error': 'Cannot delete your own account'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.delete()
            return Response(
                {'message': 'User deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        except UserModel.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class DeleteAccountAPI(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        try:
            # Check if request already exists
            if hasattr(user, 'deletion_request'):
                return Response(
                    {"message": "Deletion request already submitted."},
                    status=status.HTTP_200_OK
                )
            
            # Create deletion request
            from .models import AccountDeletionRequest
            AccountDeletionRequest.objects.create(user=user, reason="User requested deletion")
            
            return Response(
                {"message": "Deletion request submitted successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to submit request: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

# ================= ADMIN DELETION REQUESTS =================

from .serializers import AccountDeletionRequestSerializer
from .models import AccountDeletionRequest

class AdminDeletionRequestListAPI(generics.ListAPIView):
    """List all pending account deletion requests."""
    queryset = AccountDeletionRequest.objects.all()
    serializer_class = AccountDeletionRequestSerializer
    permission_classes = [permissions.IsAdminUser]

class AdminDeletionActionAPI(APIView):
    """Approve or Reject a deletion request."""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        action = request.data.get('action') # 'approve' or 'reject'
        
        try:
            deletion_request = AccountDeletionRequest.objects.get(pk=pk)
        except AccountDeletionRequest.DoesNotExist:
            return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            # Soft Delete: Determine logic. User wants to delete user.
            user = deletion_request.user
            user.delete() # This cascades and deletes the request too
            return Response({"message": "User account permanently deleted."}, status=status.HTTP_200_OK)
        
        elif action == 'reject':
            # Just delete the request, keep user
            deletion_request.delete()
            return Response({"message": "Deletion request rejected."}, status=status.HTTP_200_OK)
        
        else:
            return Response({"error": "Invalid action. Use 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)
