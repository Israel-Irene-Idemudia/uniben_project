
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
