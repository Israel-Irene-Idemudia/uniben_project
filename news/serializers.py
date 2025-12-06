from rest_framework import serializers
from .models import News
from accounts.serializers import UserSerializer

class NewsSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = News
        fields = ['id', 'title', 'content', 'image', 'author', 'created_at', 'updated_at', 
                  'for_all', 'faculty', 'department', 'level']
        read_only_fields = ['author', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Author will be set by the view's perform_create
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Don't allow changing the author
        validated_data.pop('author', None)
        return super().update(instance, validated_data)
