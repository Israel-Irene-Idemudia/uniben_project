from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Faculty

# Serializer for default User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

# Serializer for Faculty/profile
class FacultySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Faculty
        fields = ['user', 'department', 'course_area', 'level']

# Registration serializer that creates both User and Faculty
class RegisterSerializer(serializers.ModelSerializer):
    department = serializers.CharField(write_only=True)
    course_area = serializers.CharField(write_only=True)
    level = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'department', 'course_area', 'level']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        department = validated_data.pop('department', None)
        course_area = validated_data.pop('course_area', None)
        level = validated_data.pop('level', None)

        user = User.objects.create_user(**validated_data)
        Faculty.objects.create(
            user=user,
            department=department,
            course_area=course_area,
            level=level
        )
        return user
