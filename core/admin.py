from django.contrib import admin
from .models import Faculty, Department, Course

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty")
    list_filter = ("faculty",)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "level", "department")
    list_filter = ("level", "department")
    search_fields = ("code", "name")
