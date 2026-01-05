from django.contrib import admin
from .models import Material

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_verified', 'uploaded_at')
    search_fields = ('title', 'description')
    list_filter = ('category', 'is_verified', 'uploaded_at')
    actions = ['mark_as_verified']

    @admin.action(description='Mark selected materials as verified')
    def mark_as_verified(self, request, queryset):
        rows_updated = queryset.update(is_verified=True)
        self.message_user(request, f"{rows_updated} material(s) successfully verified.")

