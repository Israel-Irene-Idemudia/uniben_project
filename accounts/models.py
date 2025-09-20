# accounts/models.py
from django.db import models
from django.conf import settings


class Faculty(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        unique=True,
        null=True,   # ✅ allow missing user for now
        blank=True   # ✅ allow admin save without user
    )
    department = models.CharField(max_length=100)
    course_area = models.CharField(max_length=100)
    level = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.department} - {self.level}"
