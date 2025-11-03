from django.contrib import admin
from .models import Course, Faculty, Department, CourseArea, Level

class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'level', 'department', 'faculty', 'course_area')
    list_filter = ('level', 'department', 'faculty')
    search_fields = ('title', 'code')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'code', 'level', 'faculty', 'department', 'course_area')
        }),
    )

admin.site.register(Course, CourseAdmin)
admin.site.register(Faculty)
admin.site.register(Department)
admin.site.register(CourseArea)
admin.site.register(Level)
