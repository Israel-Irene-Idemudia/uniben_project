from django.contrib import admin
from .models import News

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "for_all", "faculty", "department", "level", "created_at", "author")
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
            "fields": ("created_at", "author"),
        }),
    )

    readonly_fields = ("created_at",)

    # Optional: auto-set author
    def save_model(self, request, obj, form, change):
        if not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.for_all:
            return self.readonly_fields + ("faculty", "department", "level")
        return self.readonly_fields
