from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import StudentDepartmentHistory, UserProfile
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

