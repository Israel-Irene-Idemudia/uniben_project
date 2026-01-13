from rest_framework import serializers
from .models import Material

class MaterialSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    
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
