from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer

UserModel = get_user_model()

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # The frontend sends 'username', which could be a username or an email.
        identifier = attrs.get('username')

        # Try to find a user by either email or username
        user = UserModel.objects.filter(email=identifier).first()
        if not user:
            user = UserModel.objects.filter(username=identifier).first()

        # If a user is found, use their actual username for validation.
        if user:
            attrs['username'] = user.username
        
        # Run the default validation.
        data = super().validate(attrs)
        
        # Add custom claims to the token response.
        data['username'] = self.user.username
        data['email'] = self.user.email
        
        return data

class MyTokenObtainPairView(TokenObtainPairView):
    """
    Custom view for obtaining a token pair, allowing login via email or username.
    """
    serializer_class = MyTokenObtainPairSerializer

class RegisterView(APIView):
    """
    Handles new user registration.
    """
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "username": serializer.data.get('username'),
                "email": serializer.data.get('email'),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    permission_classes = [AllowAny]

