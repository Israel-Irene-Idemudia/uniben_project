from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import News
from core.notifications import send_notification

@receiver(post_save, sender=News)
def notify_news(sender, instance, created, **kwargs):
    if created:
        send_notification(
            title="📰 News Update",
            message=instance.title
        )
