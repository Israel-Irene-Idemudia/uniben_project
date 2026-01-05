from django.contrib import admin
from .models import Faculty, Department, CourseArea, Level, Course, ContactMessage

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty")
    list_filter = ("faculty",)

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
