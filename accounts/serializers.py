
from rest_framework import serializers
from django.contrib.auth import get_user_model
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
        from .models import UserProfile
        model = UserProfile
        fields = ['user', 'faculty', 'department', 'level', 'course_area']

class RegisterSerializer(serializers.ModelSerializer):
    faculty_id = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.all(), source='userprofile.faculty', write_only=True
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='userprofile.department', write_only=True
    )
    level_id = serializers.PrimaryKeyRelatedField(
        queryset=Level.objects.all(), source='userprofile.level', write_only=True
    )
    course_area_id = serializers.PrimaryKeyRelatedField(
        queryset=CourseArea.objects.all(), source='userprofile.course_area', required=False, write_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'faculty_id', 'department_id', 'level_id', 'course_area_id']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        from .models import UserProfile
        profile_data = validated_data.pop('userprofile', {})
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(
            user=user,
            faculty=profile_data.get('faculty'),
            department=profile_data.get('department'),
            level=profile_data.get('level'),
            course_area=profile_data.get('course_area')
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
        from .models import UserProfile
        model = UserProfile
        fields = ['faculty_id', 'department_id', 'level_id', 'course_area_id']


# ============= SYNC SERIALIZERS =============

class UserNoteEntrySerializer(serializers.ModelSerializer):
    """Serializer for syncing user notes."""
    class Meta:
        from .models import UserNoteEntry
        model = UserNoteEntry
        fields = ['note_id', 'title', 'body', 'color', 'pinned', 'note_updated_at']


class UserGpaEntrySerializer(serializers.ModelSerializer):
    """Serializer for syncing GPA calculator entries."""
    class Meta:
        from .models import UserGpaEntry
        model = UserGpaEntry
        fields = ['course_code', 'course_name', 'unit', 'grade', 'grade_point']


class UserDebaterProgressSerializer(serializers.ModelSerializer):
    """Serializer for syncing Debater game progress."""
    class Meta:
        from .models import UserDebaterProgress
        model = UserDebaterProgress
        fields = ['beginner_score', 'intermediate_score', 'advanced_score', 'expert_score', 'updated_at']
        read_only_fields = ['updated_at']
