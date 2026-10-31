from django.contrib import admin
from .models import Faculty, Department, CourseArea, Level, Course, ContactMessage, CampusLocation, University

class NoDeleteAdmin(admin.ModelAdmin):
    """Registry rows are retired with is_active, never deleted: deleting a
    Department cascades to levels, courses, exams and student results."""

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(University)
class UniversityAdmin(NoDeleteAdmin):
    list_display = ("name", "short_name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "short_name", "code")


@admin.register(Faculty)
class FacultyAdmin(NoDeleteAdmin):
    list_display = ("name", "university", "code", "is_active")
    list_filter = ("university", "is_active")
    search_fields = ("name", "code")


@admin.register(Department)
class DepartmentAdmin(NoDeleteAdmin):
    list_display = ("name", "faculty", "code", "is_active")
    list_filter = ("faculty", "is_active")
    search_fields = ("name", "code")

@admin.register(CourseArea)
class CourseAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "department")
    list_filter = ("department",)

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "course_area")
    list_filter = ("department",)
    fields = ['name', 'department', 'course_area']  # This line adds the fields to the form

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "level")
    list_filter = ("level",)
    search_fields = ("code", "title")

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ("subject", "message", "name", "email")
    readonly_fields = ("name", "email", "subject", "message", "created_at", "user")


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "latitude", "longitude", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    list_editable = ("is_active",)  # Quick toggle for active status

