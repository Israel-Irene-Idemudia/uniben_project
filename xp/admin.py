import uuid

from django import forms
from django.contrib import admin, messages

from .admin_base import AuditedConfigAdmin, ReasonModelForm
from .models import LevelConfig, XPAdjustment, XPLedgerEntry, XPQuarantine, XPRule
from .quarantine import QuarantineError, can_quarantine, open_quarantine, quarantine_award
from .services import AdjustmentRefused, adjust_xp, check_adjustment


@admin.register(XPLedgerEntry)
class XPLedgerEntryAdmin(admin.ModelAdmin):
    """Read-only. The ledger is evidence; nothing is added, changed or deleted
    here. Use 'XP adjustments' to correct a balance."""

    list_display = ("created_at", "user", "amount", "kind", "reason_code", "source_feature")
    list_filter = ("kind", "reason_code", "source_feature")
    search_fields = ("user__username", "source_record_id", "idempotency_key")
    date_hierarchy = "created_at"
    raw_id_fields = ("user", "created_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class XPAdjustmentForm(forms.ModelForm):
    reason = forms.CharField(max_length=255, help_text="Why? Saved permanently in the audit log.")
    # A fresh token per page load acts as the idempotency key, so a double
    # click on Save cannot apply the adjustment twice.
    token = forms.CharField(widget=forms.HiddenInput, initial=lambda: uuid.uuid4().hex)

    class Meta:
        model = XPAdjustment
        fields = ("user", "amount")

    def clean(self):
        cleaned = super().clean()
        user, amount = cleaned.get("user"), cleaned.get("amount")
        if user is not None and amount is not None:
            try:
                check_adjustment(user, amount)
            except AdjustmentRefused as exc:
                raise forms.ValidationError(str(exc))
        return cleaned


@admin.register(XPAdjustment)
class XPAdjustmentAdmin(admin.ModelAdmin):
    """Award (positive) or deduct (negative) XP with a mandatory reason (BE-04.7)."""

    form = XPAdjustmentForm
    fields = ("user", "amount", "reason", "token")
    list_display = ("created_at", "user", "amount", "created_by")
    search_fields = ("user__username",)
    raw_id_fields = ("user",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(kind=XPLedgerEntry.KIND_ADJUSTMENT)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Never obj.save(): the service writes the ledger row and the audit row together.
        try:
            entry = adjust_xp(
                form.cleaned_data["user"],
                amount=form.cleaned_data["amount"],
                reason=form.cleaned_data["reason"],
                actor=request.user,
                idempotency_key=f"admin_adjust:{form.cleaned_data['token']}",
            )
        except AdjustmentRefused as exc:  # lost a race since the form check
            self.message_user(request, str(exc), level=messages.ERROR)
            return
        obj.pk = entry.pk
        obj._state.adding = False


class XPQuarantineForm(forms.ModelForm):
    """Quarantine one award (Phase 4.5). Reason mandatory; audited."""

    reason = forms.CharField(
        max_length=1000, widget=forms.Textarea,
        help_text="Why? Saved permanently in the audit log.",
    )

    class Meta:
        model = XPQuarantine
        fields = ("entry", "reason")

    def clean_entry(self):
        entry = self.cleaned_data["entry"]
        if entry.kind != XPLedgerEntry.KIND_AWARD:
            raise forms.ValidationError("Only XP awards can be quarantined.")
        if open_quarantine(entry) is not None:
            raise forms.ValidationError("This award is already quarantined.")
        return entry


@admin.register(XPQuarantine)
class XPQuarantineAdmin(admin.ModelAdmin):
    """Hold an award off the leaderboards (BE-05.5, D-22).

    Phase 4.5 minimum: add only, with the `quarantine_xp_award` permission.
    Records are read-only afterwards and never deleted. Clearing, the review
    queue and appeals are Phase 5.8 / 6.7.
    """

    form = XPQuarantineForm
    fields = ("entry", "reason")
    list_display = ("created_at", "entry", "user", "amount", "state", "source", "flagged_by")
    list_filter = ("state", "source")
    search_fields = ("entry__user__username", "entry__id")
    raw_id_fields = ("entry",)
    list_select_related = ("entry__user", "flagged_by")

    @admin.display(description="Student")
    def user(self, obj):
        return obj.entry.user

    @admin.display(description="XP")
    def amount(self, obj):
        return obj.entry.amount

    def get_readonly_fields(self, request, obj=None):
        return ("entry", "reason") if obj else ()

    def has_view_permission(self, request, obj=None):
        return can_quarantine(request.user) or super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return can_quarantine(request.user)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Never obj.save(): the service checks the permission again and
        # writes the record and its audit row together.
        try:
            record = quarantine_award(
                form.cleaned_data["entry"],
                actor=request.user,
                reason=form.cleaned_data["reason"],
                request_id=getattr(request, "request_id", None),
            )
        except QuarantineError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return
        obj.pk = record.pk
        obj._state.adding = False


class XPRuleForm(ReasonModelForm):
    class Meta:
        model = XPRule
        fields = ("action_code", "amount", "daily_cap", "diminishing_after", "diminishing_percent", "is_active", "description")


@admin.register(XPRule)
class XPRuleAdmin(AuditedConfigAdmin):
    form = XPRuleForm
    fields = XPRuleForm.Meta.fields + ("reason",)
    list_display = ("action_code", "amount", "daily_cap", "diminishing_after", "is_active")
    audit_fields = XPRuleForm.Meta.fields
    audit_prefix = "xp_rule"


class LevelConfigForm(ReasonModelForm):
    class Meta:
        model = LevelConfig
        fields = ("level", "xp_threshold", "title", "effective_from")


@admin.register(LevelConfig)
class LevelConfigAdmin(AuditedConfigAdmin):
    form = LevelConfigForm
    fields = LevelConfigForm.Meta.fields + ("reason",)
    list_display = ("level", "title", "xp_threshold", "effective_from")
    audit_fields = LevelConfigForm.Meta.fields
    audit_prefix = "level_config"
