from django import forms
from django.contrib import admin

from common.models import AuditLog, FeatureFlag, PlatformSetting
from common.services import log_audit, set_setting


def _request_id(request):
    return getattr(request, "request_id", None)


class ReasonForm(forms.ModelForm):
    """Every change made in admin must say why; the reason goes to the audit log."""

    reason = forms.CharField(
        max_length=255,
        help_text="Why is this changing? Saved permanently in the audit log.",
    )


class PlatformSettingForm(ReasonForm):
    class Meta:
        model = PlatformSetting
        fields = ("key", "value", "description")


class FeatureFlagForm(ReasonForm):
    class Meta:
        model = FeatureFlag
        fields = "__all__"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only. The log itself cannot be edited from the console."""

    list_display = ("created_at", "actor_label", "action", "target_type", "target_id", "request_id")
    list_filter = ("action", "target_type")
    search_fields = ("actor_label", "action", "target_id", "request_id", "reason")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    form = PlatformSettingForm
    fields = ("key", "value", "description", "reason")
    list_display = ("key", "value", "updated_by", "updated_at")
    search_fields = ("key", "description")

    def get_readonly_fields(self, request, obj=None):
        # A key never changes after creation; renaming would break the audit trail.
        return ("key",) if obj else ()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Go through set_setting so the change and its audit row share one path.
        # (Django admin already wraps this whole save in a transaction.)
        saved = set_setting(
            obj.key,
            obj.value,
            actor=request.user,
            reason=form.cleaned_data["reason"],
            description=obj.description,
            request_id=_request_id(request),
        )
        # The rest of the admin flow (success message, redirect) needs a saved object.
        obj.pk = saved.pk
        obj._state.adding = False


def _flag_snapshot(flag):
    return {
        "description": flag.description,
        "enabled": flag.enabled,
        "audience": flag.audience,
        "users": sorted(flag.users.values_list("pk", flat=True)),
        "departments": sorted(flag.departments.values_list("pk", flat=True)),
    }


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    form = FeatureFlagForm
    list_display = ("name", "enabled", "audience", "updated_at")
    list_filter = ("enabled", "audience")
    search_fields = ("name", "description")
    raw_id_fields = ("users",)
    filter_horizontal = ("departments",)

    def has_delete_permission(self, request, obj=None):
        # Flags are switched off, not deleted, so every change stays audited.
        return False

    def save_model(self, request, obj, form, change):
        # Snapshot BEFORE saving; users/departments are saved later in save_related.
        request._flag_before = (
            _flag_snapshot(FeatureFlag.objects.get(pk=obj.pk)) if change else None
        )
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        flag = form.instance
        before = getattr(request, "_flag_before", None)
        after = _flag_snapshot(flag)
        if before != after:
            log_audit(
                actor=request.user,
                action="flag.update" if change else "flag.create",
                target_type="FeatureFlag",
                target_id=flag.name,
                before=before,
                after=after,
                reason=form.cleaned_data["reason"],
                request_id=_request_id(request),
            )