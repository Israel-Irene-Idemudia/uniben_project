from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "department", "level"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, attrs):
        if attrs["role"] == "student" and not attrs.get("level"):
            raise serializers.ValidationError({"level": "Students must select a level."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
            role=validated_data["role"],
            department=validated_data["department"],
            level=validated_data.get("level"),
        )
        return user
