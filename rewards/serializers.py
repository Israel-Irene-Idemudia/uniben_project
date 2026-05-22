from rest_framework import serializers
from .models import Redemption

class RedemptionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Redemption
        fields = ['id', 'username', 'reward_type', 'point_cost', 'phone', 'network', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']
