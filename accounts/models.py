
from django.db import models
from django.conf import settings
from core.models import Faculty, Department, Level, CourseArea

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    faculty = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True)
    course_area = models.ForeignKey(CourseArea, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username
