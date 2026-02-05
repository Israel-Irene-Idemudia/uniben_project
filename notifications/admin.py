from django.contrib import admin
from .models import InAppNotification, SupportTicket


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type',
                    'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['subject', 'user', 'status', 'created_at', 'replied_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'subject', 'message', 'email']
    readonly_fields = ['created_at', 'updated_at', 'replied_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Ticket Information', {
            'fields': ('user', 'name', 'email', 'subject', 'message', 'status')
        }),
        ('Admin Reply', {
            'fields': ('admin_reply', 'replied_by', 'replied_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
