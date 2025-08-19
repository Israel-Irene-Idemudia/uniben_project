from django.contrib import admin
from .models import Faculty, Department, CourseArea, Level, Course
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

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "unit", "level")
    list_filter = ("level",)
    search_fields = ("code", "title")
