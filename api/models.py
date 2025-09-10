from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.title}"


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    options = models.JSONField()
    answer = models.CharField(max_length=200)

    def __str__(self):
        return f"Q: {self.text[:50]}..."

