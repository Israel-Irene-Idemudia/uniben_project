from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Faculty

class FacultyInline(admin.StackedInline):
    model = Faculty
    can_delete = False
    verbose_name_plural = 'Faculty'

class CustomUserAdmin(UserAdmin):
    inlines = (FacultyInline, )

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
