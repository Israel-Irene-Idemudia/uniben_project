"""Contribution rule admin (Phase 4.2).

Drafts are edited freely (with a reason, audited as one before/after row
that includes the activities). Activation and retirement are transitions
that call leaderboards.services, which checks the activate permission and
refuses incomplete drafts. Active and retired sets are read-only; use the
"Copy to a new draft" action to change a published rule. No deletes.
"""
from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html_join

from .models import ContributionRuleItem, ContributionRuleSet
from .services import (
    RuleSetError,
    activate_rule_set,
    copy_to_draft,
    readiness_problems,
    record_draft_edit,
    retire_rule_set,
    snapshot,
)

TRANSITION_NONE = ""
TRANSITION_ACTIVATE = "activate"
TRANSITION_RETIRE = "retire"
DRAFT_FIELDS = ("name", "university", "summary", "student_cap", "uncapped")


class ContributionRuleSetForm(forms.ModelForm):
    reason = forms.CharField(max_length=255, help_text="Why? Saved permanently in the audit log.")
    transition = forms.ChoiceField(
        required=False,
        choices=[
            (TRANSITION_NONE, "No state change"),
            (TRANSITION_ACTIVATE, "Activate (publish to students)"),
            (TRANSITION_RETIRE, "Retire"),
        ],
        help_text="Activating needs the activate permission and a complete rule. "
        "It retires the previous active rule for the same university (or the global one).",
    )

    class Meta:
        model = ContributionRuleSet
        fields = DRAFT_FIELDS

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("transition") == TRANSITION_RETIRE and not self.instance.pk:
            raise forms.ValidationError("A new rule set cannot be retired.")
        return cleaned


class ContributionRuleItemInline(admin.TabularInline):
    model = ContributionRuleItem
    extra = 1
    fields = ("xp_rule", "label", "weight", "per_student_cap")

    def _editable(self, obj) -> bool:
        return obj is None or obj.state == ContributionRuleSet.STATE_DRAFT

    def has_add_permission(self, request, obj=None):
        return self._editable(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._editable(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._editable(obj) and super().has_delete_permission(request, obj)


@admin.register(ContributionRuleSet)
class ContributionRuleSetAdmin(admin.ModelAdmin):
    form = ContributionRuleSetForm
    inlines = [ContributionRuleItemInline]
    list_display = ("name", "university", "state", "student_cap", "uncapped", "activated_at")
    list_filter = ("state", "university")
    search_fields = ("name",)
    actions = ["copy_to_new_draft"]
    readonly_fields = ("state", "readiness", "activated_at", "activated_by", "retired_at")

    def get_fields(self, request, obj=None):
        return DRAFT_FIELDS + self.readonly_fields + ("transition", "reason")

    def get_readonly_fields(self, request, obj=None):
        ro = list(self.readonly_fields)
        if obj is not None and obj.state != ContributionRuleSet.STATE_DRAFT:
            ro += list(DRAFT_FIELDS)  # published rules are frozen
        return ro

    def has_delete_permission(self, request, obj=None):
        # Archived boards will point at the rule they used; never delete.
        return False

    @admin.display(description="Ready to activate?")
    def readiness(self, obj):
        if obj is None or obj.pk is None:
            return "Save the draft first."
        if obj.state != ContributionRuleSet.STATE_DRAFT:
            return "-"
        problems = readiness_problems(obj)
        if not problems:
            return "Ready to activate."
        return format_html_join("", "<div>{}</div>", ((p,) for p in problems))

    def save_model(self, request, obj, form, change):
        # Snapshot BEFORE saving, so the audit row shows the real change.
        request._rule_set_before = snapshot(type(obj).objects.get(pk=obj.pk)) if change else None
        if change and type(obj).objects.get(pk=obj.pk).state != ContributionRuleSet.STATE_DRAFT:
            return  # frozen: only a transition may happen (in save_related)
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # Runs after the inlines are saved, so the audit row and the
        # readiness check both see the activities.
        super().save_related(request, form, formsets, change)
        obj = ContributionRuleSet.objects.get(pk=form.instance.pk)
        reason = form.cleaned_data["reason"]
        if obj.state == ContributionRuleSet.STATE_DRAFT:
            record_draft_edit(obj, before=getattr(request, "_rule_set_before", None), actor=request.user, reason=reason)
        transition = form.cleaned_data.get("transition") or TRANSITION_NONE
        try:
            if transition == TRANSITION_ACTIVATE:
                activate_rule_set(obj, actor=request.user, reason=reason)
            elif transition == TRANSITION_RETIRE:
                retire_rule_set(obj, actor=request.user, reason=reason)
        except RuleSetError as exc:
            # The draft edits are kept; only the state change is refused.
            self.message_user(
                request, "Not activated/retired: " + " ".join(exc.problems), level=messages.ERROR
            )

    @admin.action(description="Copy to a new draft")
    def copy_to_new_draft(self, request, queryset):
        for rule_set in queryset:
            copy = copy_to_draft(rule_set, actor=request.user, reason="Admin action: copy to a new draft")
            self.message_user(request, f"Draft {copy.pk} created from rule set {rule_set.pk}.")
