from django.contrib import admin
from .models import UserActivity

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'action', 'timestamp', 'metadata']
    date_hierarchy = 'timestamp'
