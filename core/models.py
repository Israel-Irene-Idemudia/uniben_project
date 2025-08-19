# core/models.py
from django.db import models

class Faculty(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=200)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="departments")

    def __str__(self):
        return self.name


class CourseArea(models.Model):  # optional (for departments that have areas)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="course_areas")

    def __str__(self):
        return f"{self.department.name} - {self.name}"


class Level(models.Model):
    name = models.CharField(max_length=20)  # e.g. "100L", "200L"
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="levels")
    course_area = models.ForeignKey(CourseArea, on_delete=models.CASCADE, null=True, blank=True, related_name="levels")

    def __str__(self):
        return f"{self.department.name} - {self.name}"


class Course(models.Model):
    code = models.CharField(max_length=20)   # e.g. "MTH101"
    title = models.CharField(max_length=200)
    unit = models.IntegerField()
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="courses")

    def __str__(self):
        return f"{self.code} - {self.title}"
