# accounts/profile_serializers.py

from rest_framework import serializers
from .models import UserTimetableEntry, UserPreferences


class UserTimetableEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTimetableEntry
        fields = [
            'id',
            'subject',
            'day',
            'time',
            'alarm_enabled',
            'alarm_times',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Automatically set the user from the request context
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = [
            'notifications_enabled',
            'notification_sound',
            'theme',
            'other_settings',
            'updated_at',
        ]
        read_only_fields = ['updated_at']
