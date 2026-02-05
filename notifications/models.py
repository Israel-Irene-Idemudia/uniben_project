from django.db import models
from django.conf import settings


class InAppNotification(models.Model):
    """
    In-app notifications for users.
    Can be used for support replies, announcements, reminders, etc.
    """
    NOTIFICATION_TYPES = [
        ('support_reply', 'Support Reply'),
        ('announcement', 'System Announcement'),
        ('reminder', 'Reminder'),
        ('news', 'News Update'),
        ('event', 'Event Update'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='general'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()

    # Optional metadata for linking to specific content
    related_id = models.IntegerField(
        null=True, blank=True, help_text="ID of related object (news, event, etc.)")
    related_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Type of related object (news, event, support_ticket, etc.)"
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title} ({'Read' if self.is_read else 'Unread'})"


class SupportTicket(models.Model):
    """
    Support tickets submitted by users via Contact Us form.
    Allows tracking and replying to user inquiries.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets'
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Admin reply
    admin_reply = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_replies'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.user.username} ({self.status})"
