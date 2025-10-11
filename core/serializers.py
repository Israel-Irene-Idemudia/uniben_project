# core/serializers.py
from rest_framework import serializers
from core.models import Course

class CourseSerializer(serializers.ModelSerializer):
    level_id = serializers.IntegerField(source='level.id', read_only=True)
    level_name = serializers.CharField(source='level.name', read_only=True)

    department_id = serializers.IntegerField(source='level.department.id', read_only=True)
    department_name = serializers.CharField(source='level.department.name', read_only=True)

    faculty_id = serializers.IntegerField(source='level.department.faculty.id', read_only=True)
    faculty_name = serializers.CharField(source='level.department.faculty.name', read_only=True)

    course_area_id = serializers.IntegerField(source='level.course_area.id', read_only=True, allow_null=True)
    course_area_name = serializers.CharField(source='level.course_area.name', read_only=True, allow_null=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'code',
            'title',
            'level_id', 'level_name',
            'department_id', 'department_name',
            'faculty_id', 'faculty_name',
            'course_area_id', 'course_area_name',
        ]