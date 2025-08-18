from django.db import models
from django.contrib.auth.models import AbstractUser

# Custom User model
class User(AbstractUser):
    LEVEL_CHOICES = [
        ('100', '100 Level'),
        ('200', '200 Level'),
        ('300', '300 Level'),
        ('400', '400 Level'),
        ('500', '500 Level'),
    ]
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=3, choices=LEVEL_CHOICES, blank=True, null=True)

    def __str__(self):
        return self.username


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)  # e.g., CPE

    def __str__(self):
        return self.name


# Optional "sub-area" under a department
class CourseArea(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='course_areas')
    name = models.CharField(max_length=100)  # e.g., "Software Engineering"

    def __str__(self):
        return f"{self.department.name} - {self.name}"


class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    course_area = models.ForeignKey(CourseArea, on_delete=models.SET_NULL, null=True, blank=True)  # optional
    code = models.CharField(max_length=10)  # e.g., MTH101
    title = models.CharField(max_length=200)
    level = models.CharField(max_length=3)  # e.g., 100, 200

    def __str__(self):
        area = f" ({self.course_area.name})" if self.course_area else ""
        return f"{self.code} - {self.title}{area}"
