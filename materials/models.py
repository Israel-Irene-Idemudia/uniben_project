from django.db import models
from django.contrib.auth.models import User
from cloudinary_storage.storage import MediaCloudinaryStorage


class Material(models.Model):
    CATEGORY_CHOICES = [
        ('course', 'Course Material'),
        ('past_question', 'Past Question'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='course')

    # Add course/subject field for grouping
    course_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Course code (e.g., MTH101, ENG102, CSC201)"
    )
    course_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Full course name"
    )

    file = models.FileField(upload_to='materials/',
                            storage=MediaCloudinaryStorage())
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True,
                             blank=True, related_name='uploaded_materials')  # Track uploader
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['course_code', '-uploaded_at']
        indexes = [
            models.Index(fields=['course_code', 'is_verified']),
            models.Index(fields=['category', 'is_verified']),
        ]

    def __str__(self):
        if self.course_code:
            return f"{self.course_code} - {self.title}"
        return self.title
