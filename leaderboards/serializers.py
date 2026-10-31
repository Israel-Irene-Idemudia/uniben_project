from rest_framework import serializers

from .models import ContributionRuleItem, ContributionRuleSet


class ContributionRuleItemSerializer(serializers.ModelSerializer):
    action_code = serializers.CharField(source="xp_rule.action_code", read_only=True)

    class Meta:
        model = ContributionRuleItem
        # weight is a decimal STRING ("1.50") so both clients show it verbatim.
        fields = ["action_code", "label", "weight", "per_student_cap"]
        read_only_fields = fields


class ContributionRuleSetSerializer(serializers.ModelSerializer):
    scope = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    activities = ContributionRuleItemSerializer(source="items", many=True, read_only=True)

    class Meta:
        model = ContributionRuleSet
        fields = [
            "id", "name", "scope", "university", "summary",
            "student_cap", "uncapped", "activated_at", "activities",
        ]
        read_only_fields = fields

    def get_scope(self, obj) -> str:
        return "global" if obj.university_id is None else "university"

    def get_university(self, obj):
        uni = obj.university
        if uni is None:
            return None
        return {"id": uni.id, "name": uni.name, "code": uni.code}
