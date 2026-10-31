from rest_framework import serializers

from .models import XPLedgerEntry


class XPEntrySerializer(serializers.ModelSerializer):
    """What a student may see of their own ledger. No idempotency key, no
    metadata, no internal ids."""

    class Meta:
        model = XPLedgerEntry
        fields = ["id", "amount", "kind", "reason_code", "source_feature", "created_at"]
        read_only_fields = fields
