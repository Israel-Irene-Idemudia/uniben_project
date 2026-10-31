from rest_framework import serializers

from core.models import Department, Faculty, University


class V1UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = ["id", "name", "code", "short_name"]


class V1FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ["id", "name", "code"]


class V1DepartmentSerializer(serializers.ModelSerializer):
    faculty_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "faculty_id"]