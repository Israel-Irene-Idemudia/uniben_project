from django.contrib import admin

from common.models import FeatureFlag


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "audience", "updated_at")
    list_filter = ("enabled", "audience")
    search_fields = ("name", "description")
    raw_id_fields = ("users",)
    filter_horizontal = ("departments",)