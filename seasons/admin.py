"""Season admin: create, reschedule, open and close, every action audited.

The form never saves the model itself. save_model calls seasons.services, so
the state change and its AuditLog row are written in one transaction.
"""
from django import forms
from django.contrib import admin, messages

from .models import Season
from .services import (
    SeasonError,
    close_season,
    create_season,
    open_season,
    reschedule_season,
    validate_window,
)

TRANSITION_NONE = ""
TRANSITION_OPEN = "open"
TRANSITION_CLOSE = "close"


class SeasonAdminForm(forms.ModelForm):
    reason = forms.CharField(max_length=255, help_text="Why? Saved permanently in the audit log.")
    transition = forms.ChoiceField(
        required=False,
        choices=[(TRANSITION_NONE, "No state change"), (TRANSITION_OPEN, "Open this season"), (TRANSITION_CLOSE, "Close this season")],
        help_text="Closing is final: a closed season is never reopened.",
    )

    class Meta:
        model = Season
        fields = ("name", "kind", "starts_at", "ends_at")

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        kind = cleaned.get("kind", instance.kind if instance.pk else None)
        starts_at = cleaned.get("starts_at", instance.starts_at if instance.pk else None)
        ends_at = cleaned.get("ends_at", instance.ends_at if instance.pk else None)
        if kind and starts_at and ends_at:
            try:
                validate_window(kind, starts_at, ends_at, exclude_pk=instance.pk)
            except SeasonError as exc:
                raise forms.ValidationError(str(exc))
        transition = cleaned.get("transition")
        if transition and not instance.pk and transition == TRANSITION_CLOSE:
            raise forms.ValidationError("A new season cannot be closed.")
        return cleaned


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    form = SeasonAdminForm
    list_display = ("name", "kind", "state", "starts_at", "ends_at")
    list_filter = ("kind", "state")
    search_fields = ("name",)
    readonly_fields = ("state", "opened_at", "closed_at")

    def get_fields(self, request, obj=None):
        return ("name", "kind", "starts_at", "ends_at", "state", "opened_at", "closed_at", "transition", "reason")

    def get_readonly_fields(self, request, obj=None):
        ro = list(self.readonly_fields)
        if obj is not None:
            ro.append("kind")  # a season never changes kind
            if obj.state != Season.STATE_SCHEDULED:
                ro += ["name", "starts_at", "ends_at"]
        return ro

    def has_delete_permission(self, request, obj=None):
        # Archived boards point at seasons; retire nothing by deleting.
        return False

    def save_model(self, request, obj, form, change):
        data = form.cleaned_data
        reason = data["reason"]
        transition = data.get("transition") or TRANSITION_NONE
        try:
            if not change:
                season = create_season(
                    name=obj.name, kind=obj.kind, starts_at=obj.starts_at, ends_at=obj.ends_at,
                    actor=request.user, reason=reason,
                )
            else:
                season = Season.objects.get(pk=obj.pk)
                if season.state == Season.STATE_SCHEDULED and any(
                    f in form.changed_data for f in ("name", "starts_at", "ends_at")
                ):
                    season = reschedule_season(
                        season, name=obj.name, starts_at=obj.starts_at, ends_at=obj.ends_at,
                        actor=request.user, reason=reason,
                    )
            if transition == TRANSITION_OPEN:
                season = open_season(season, actor=request.user, reason=reason)
            elif transition == TRANSITION_CLOSE:
                season = close_season(season, actor=request.user, reason=reason)
        except SeasonError as exc:
            # Lost a race since the form check, or an invalid transition.
            self.message_user(request, str(exc), level=messages.ERROR)
            if not change:
                return
            season = Season.objects.get(pk=obj.pk)
        obj.pk = season.pk
        obj._state.adding = False
