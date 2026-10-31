from django.contrib import admin

from xp.admin_base import AuditedConfigAdmin, ReasonModelForm

from .models import RewardCatalog


class RewardCatalogForm(ReasonModelForm):
    class Meta:
        model = RewardCatalog
        fields = ("reward_type", "point_cost", "is_active")


@admin.register(RewardCatalog)
class RewardCatalogAdmin(AuditedConfigAdmin):
    """The price list (D-1). Changes need a reason and are audited. Retire a
    reward by switching is_active off; deleting is disabled."""

    form = RewardCatalogForm
    fields = RewardCatalogForm.Meta.fields + ("reason",)
    list_display = ("reward_type", "point_cost", "is_active", "updated_at")
    audit_fields = RewardCatalogForm.Meta.fields
    audit_prefix = "reward_catalog"
