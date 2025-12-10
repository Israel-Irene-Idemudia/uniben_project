from django.contrib import admin
from .models import News

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "for_all", "faculty", "department", "level", "created_at", "updated_at", "author")
    list_filter = ("for_all", "faculty", "department", "level")
    search_fields = ("title", "content")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {
            "fields": ("title", "content", "image")
        }),
        ("Visibility Options", {
            "fields": ("for_all", "faculty", "department", "level"),
            "description": "Choose who should see this news. If 'For all' is checked, it overrides faculty, department, and level."
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at", "author"),
        }),
    )

    readonly_fields = ("created_at", "updated_at")

    # Auto-set author if empty
    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            from django.contrib import messages
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save news: {str(e)}", exc_info=True)
            messages.error(request, f"Failed to create news: {str(e)}")
            raise

    # Make visibility fields readonly if 'for_all' is checked
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.for_all:
            return self.readonly_fields + ("faculty", "department", "level")
        return self.readonly_fields
