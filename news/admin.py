from django.contrib import admin
from django.utils.html import format_html
from .models import News

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at', 'image_preview')
    search_fields = ('title', 'content')

    def image_preview(self, obj):
        if obj.image:  # check if image exists
            return format_html('<img src="{}" style="width: 80px; height: auto;" />', obj.image.url)
        return "No Image"

    image_preview.short_description = "Preview"
