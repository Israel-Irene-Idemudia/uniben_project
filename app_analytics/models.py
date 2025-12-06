from django.db import models
from django.conf import settings

class UserActivity(models.Model):
    """Track user actions for analytics"""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('cbt_start', 'CBT Quiz Started'),
        ('cbt_submit', 'CBT Quiz Submitted'),
        ('pdf_view', 'PDF Viewed'),
        ('news_view', 'News Viewed'),
        ('event_view', 'Event Viewed'),
        ('timetable_view', 'Timetable Viewed'),
        ('map_view', 'Map Viewed'),
        ('ai_chat', 'AI Chat Used'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"
