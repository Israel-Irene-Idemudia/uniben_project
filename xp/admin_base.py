"""Shared admin plumbing: edit configuration only with a reason, and audit it.

Used for XP rules, the level curve and the reward catalogue (BE-04.4,
BE-20.1, D-1): these decide what students earn and pay, so a change must
leave a permanent who/what/why/when row in the audit log.
"""
from django import forms
from django.contrib import admin

from common.services import log_audit


def _snapshot(obj, fields):
    out = {}
    for name in fields:
        value = getattr(obj, name)
        out[name] = value if isinstance(value, (int, str, bool, type(None))) else str(value)
    return out


class ReasonModelForm(forms.ModelForm):
    reason = forms.CharField(max_length=255, help_text="Why? Saved permanently in the audit log.")


class AuditedConfigAdmin(admin.ModelAdmin):
    """Subclass, set `audit_fields` and `audit_prefix`, and use a form that
    extends ReasonModelForm (with 'reason' in `fields`)."""

    audit_fields = ()
    audit_prefix = "config"

    def has_delete_permission(self, request, obj=None):
        # Retire a row (is_active off or a newer effective_from); never delete,
        # so history stays explainable.
        return False

    def save_model(self, request, obj, form, change):
        before = None
        if change:
            before = _snapshot(type(obj).objects.get(pk=obj.pk), self.audit_fields)
        super().save_model(request, obj, form, change)
        log_audit(
            actor=request.user,
            action=f"{self.audit_prefix}.{'update' if change else 'create'}",
            target_type=type(obj).__name__,
            target_id=obj.pk,
            before=before,
            after=_snapshot(obj, self.audit_fields),
            reason=form.cleaned_data["reason"],
            request_id=getattr(request, "request_id", None),
        )
