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
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='course')
    file = models.FileField(upload_to='materials/', storage=MediaCloudinaryStorage())
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='uploaded_materials')  # Track uploader
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title



