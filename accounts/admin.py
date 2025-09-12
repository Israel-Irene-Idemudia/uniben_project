from django.contrib import admin
from .models import Faculty

class FacultyAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    search_fields = ('user__username', 'department')

admin.site.register(Faculty, FacultyAdmin)
