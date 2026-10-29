from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from common.services import log_audit

from .models import DepartmentChangeApproval, StudentDepartmentHistory, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )


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