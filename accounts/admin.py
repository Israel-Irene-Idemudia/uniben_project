from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from accounts.account_state import ACTIVE, DELETED, SUSPENDED, set_account_state
from accounts.session_revocation import revoke_all_sessions
from common.services import log_audit

from .models import (
    AccountStatus,
    AuthEvent,
    DepartmentChangeApproval,
    StudentDepartmentHistory,
    UserProfile,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'


@admin.action(description="Sign out selected users everywhere (revoke refresh tokens)")
def sign_out_everywhere(modeladmin, request, queryset):
    total = 0
    users = list(queryset)
    for user in users:
        total += revoke_all_sessions(
            user, actor=request.user, reason="Admin action: sign out everywhere"
        )
    modeladmin.message_user(
        request,
        f"Revoked {total} login(s) for {len(users)} user(s). "
        "Access tokens already issued expire within 15 minutes.",
    )


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )
    actions = [sign_out_everywhere]


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(StudentDepartmentHistory)
class StudentDepartmentHistoryAdmin(admin.ModelAdmin):
    """Read-only: history is written by the system, never edited by hand."""

    list_display = ("user", "department_name", "faculty_name", "effective_from", "effective_to", "reason")
    search_fields = ("user__username", "department_name")
    raw_id_fields = ("user", "changed_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DepartmentChangeApproval)
class DepartmentChangeApprovalAdmin(admin.ModelAdmin):
    """Approve ONE extra department change for a student. Audited."""

    list_display = ("user", "approved_by", "reason", "created_at", "used_at")
    fields = ("user", "reason")
    raw_id_fields = ("user",)
    search_fields = ("user__username",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.approved_by = request.user
        super().save_model(request, obj, form, change)
        log_audit(
            actor=request.user,
            action="department.change_approved",
            target_type="DepartmentChangeApproval",
            target_id=obj.pk,
            after={"user_id": obj.user_id},
            reason=obj.reason,
            request_id=getattr(request, "request_id", None),
        )


@admin.register(AuthEvent)
class AuthEventAdmin(admin.ModelAdmin):
    """The auth log (BE-01.4). Read-only: it is evidence, not something to edit."""

    list_display = ("created_at", "kind", "success", "detail", "user", "ip_address")
    list_filter = ("kind", "success")
    search_fields = ("user__username", "ip_address")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AccountStatusForm(forms.ModelForm):
    """Suspend or reinstate. A reason is always required. 'Deleted' cannot be
    chosen here: it is set only by the anonymising delete."""

    state = forms.ChoiceField(choices=[(ACTIVE, "Active"), (SUSPENDED, "Suspended")])
    reason = forms.CharField(
        max_length=255, help_text="Why? Saved permanently in the audit log."
    )

    class Meta:
        model = AccountStatus
        fields = ("user", "state", "reason")

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk and self.instance.state == DELETED:
            raise forms.ValidationError("A deleted account cannot change state.")
        return cleaned


@admin.register(AccountStatus)
class AccountStatusAdmin(admin.ModelAdmin):
    """Suspend or reinstate a student (BE-01.5). Every change is audited."""

    form = AccountStatusForm
    fields = ("user", "state", "reason")
    list_display = ("user", "state", "reason", "changed_by", "updated_at")
    list_filter = ("state",)
    search_fields = ("user__username",)
    raw_id_fields = ("user",)

    def get_readonly_fields(self, request, obj=None):
        return ("user",) if obj else ()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Go through the service so the change and its audit row share one path.
        saved = set_account_state(
            obj.user,
            obj.state,
            actor=request.user,
            reason=obj.reason,
            request_id=getattr(request, "request_id", None),
        )
        obj.pk = saved.pk
        obj._state.adding = False