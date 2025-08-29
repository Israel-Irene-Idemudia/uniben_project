from rest_framework import serializers
from .models import News

class NewsSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = News
        fields = ['id', 'title', 'content', 'image', 'author', 'created_at', 'updated_at']
