from django.db import models
from django.conf import settings


class AIUploadLog(models.Model):
    """
    Tracks file uploads in AI chat for rate limiting.
    Limits: 2 PDFs + 3 images per user per day.
    """
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('image', 'Image'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.file_type} @ {self.uploaded_at}"
