from django.contrib import admin
from .models import Material

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'uploaded_at')
    search_fields = ('title', 'description')
    list_filter = ('category', 'uploaded_at')

