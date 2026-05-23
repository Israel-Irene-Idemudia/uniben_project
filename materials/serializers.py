from rest_framework import serializers
from .models import Material

class MaterialSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    faculty_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = '__all__'
    
    def get_uploaded_by(self, obj):
        """Return user info with email"""
        if obj.user:
            return {
                'username': obj.user.username,
                'email': obj.user.email,
                'id': obj.user.id
            }
        return None

    def get_faculty_name(self, obj):
        return obj.faculty.name if obj.faculty else None
        
    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

