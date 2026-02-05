from rest_framework import serializers
from .models import InAppNotification, SupportTicket


class InAppNotificationSerializer(serializers.ModelSerializer):
    """Serializer for in-app notifications"""

    class Meta:
        model = InAppNotification
        fields = [
            'id',
            'notification_type',
            'title',
            'message',
            'related_id',
            'related_type',
            'is_read',
            'created_at',
            'read_at',
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    """Serializer for support tickets"""
    user_username = serializers.CharField(
        source='user.username', read_only=True)
    replied_by_username = serializers.CharField(
        source='replied_by.username', read_only=True, allow_null=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'user',
            'user_username',
            'name',
            'email',
            'subject',
            'message',
            'status',
            'admin_reply',
            'replied_at',
            'replied_by',
            'replied_by_username',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at',
                            'updated_at', 'replied_at', 'replied_by']


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating support tickets"""

    class Meta:
        model = SupportTicket
        fields = ['name', 'email', 'subject', 'message']
