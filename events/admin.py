from django.contrib import admin
from django.utils.html import format_html
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_date', 'location', 'image_preview')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 80px; height: auto;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "Preview"
    
    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            from django.contrib import messages
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save event: {str(e)}", exc_info=True)
            messages.error(request, f"Failed to create event: {str(e)}")
            raise

