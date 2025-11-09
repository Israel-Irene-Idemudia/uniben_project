
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile
from core.models import Department, CourseArea, Level, Faculty

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    faculty = serializers.StringRelatedField()
    department = serializers.StringRelatedField()
    level = serializers.StringRelatedField()
    course_area = serializers.StringRelatedField()

    class Meta:
        model = UserProfile
        fields = ['user', 'faculty', 'department', 'level', 'course_area']

class RegisterSerializer(serializers.ModelSerializer):
    faculty_id = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.all(), write_only=True
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), write_only=True
    )
    level_id = serializers.PrimaryKeyRelatedField(
        queryset=Level.objects.all(), write_only=True
    )
    course_area_id = serializers.PrimaryKeyRelatedField(
        queryset=CourseArea.objects.all(), required=False, write_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'faculty_id', 'department_id', 'level_id', 'course_area_id']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        faculty = validated_data.pop('faculty_id')
        department = validated_data.pop('department_id')
        level = validated_data.pop('level_id')
        course_area = validated_data.pop('course_area_id', None)
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(
            user=user,
            faculty=faculty,
            department=department,
            level=level,
            course_area=course_area
        )
        return user

class UpdateProfileSerializer(serializers.ModelSerializer):
    faculty_id = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.all(), source='faculty', write_only=True
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', write_only=True
    )
    level_id = serializers.PrimaryKeyRelatedField(
        queryset=Level.objects.all(), source='level', write_only=True
    )
    course_area_id = serializers.PrimaryKeyRelatedField(
        queryset=CourseArea.objects.all(), source='course_area', required=False, allow_null=True
    )

    class Meta:
        model = UserProfile
        fields = ['faculty_id', 'department_id', 'level_id', 'course_area_id']
