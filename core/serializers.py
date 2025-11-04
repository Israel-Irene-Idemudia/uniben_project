# core/serializers.py
from rest_framework import serializers
from core.models import Faculty, Department, CourseArea, Course

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'name']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']

class CourseAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseArea
        fields = ['id', 'name']

class CourseSerializer(serializers.ModelSerializer):
    # Rename fields to match the Flutter app's expectations
    level = serializers.CharField(source='level.name', read_only=True)
    department = serializers.CharField(source='level.department.name', read_only=True)
    faculty = serializers.CharField(source='level.department.faculty.name', read_only=True)
    course_area = serializers.CharField(source='level.course_area.name', read_only=True, allow_null=True)

    # Rename 'code' and 'title' for consistency
    course_code = serializers.CharField(source='code')
    course_title = serializers.CharField(source='title')

    class Meta:
        model = Course
        # Define the fields that the JSON response will include
        fields = [
            'level',
            'course_code',
            'course_title',
            'course_area',
            'department',
            'faculty',
        ]
