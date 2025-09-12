from rest_framework import serializers
from .models import News
from accounts.serializers import UserSerializer

class NewsSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = News
        fields = ['id', 'title', 'content', 'image', 'author', 'created_at', 'updated_at']
