from rest_framework import serializers

from .models import Season


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ["id", "name", "kind", "state", "starts_at", "ends_at"]
        read_only_fields = fields
