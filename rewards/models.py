from django.db import models
from django.conf import settings

class Redemption(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Dispatch'),
        ('dispatched', 'Dispatched'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    reward_type = models.CharField(max_length=100)
    point_cost = models.IntegerField(default=50)
    phone = models.CharField(max_length=20)
    network = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.reward_type} ({self.status})"
