from rest_framework import serializers
from .models import Material

class MaterialSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    
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

