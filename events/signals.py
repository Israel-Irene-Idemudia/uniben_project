from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Event
from core.notifications import send_notification

@receiver(post_save, sender=Event)
def notify_event(sender, instance, created, **kwargs):
    if created:
        send_notification(
            title="📅 New Event",
            message=f"{instance.title} on {instance.event_date.strftime('%b %d, %Y %I:%M %p')}"
        )
