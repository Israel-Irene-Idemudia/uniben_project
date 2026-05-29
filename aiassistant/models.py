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

class StudentAIPromptTracker(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subject_room = models.CharField(max_length=50) # e.g., 'physics', 'math', 'chemistry'
    
    # Text Counters for the high-reasoning smart engine
    deep_study_messages_used = models.IntegerField(default=0)
    has_active_premium_pass = models.BooleanField(default=False)
    pass_expiration_datetime = models.DateTimeField(null=True, blank=True)
    
    # Universal Media Counters (Reset daily via background automation task)
    daily_images_uploaded = models.IntegerField(default=0)
    daily_audio_memos_used = models.IntegerField(default=0)
    last_interaction_date = models.DateField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'subject_room')
        verbose_name = "Student AI Prompt Tracker"
        
    def is_deep_study_allowed(self):
        # Verification sequence for the smart engine track
        if self.has_active_premium_pass:
            return True
        if self.deep_study_messages_used < 50:
            return True
        return False
