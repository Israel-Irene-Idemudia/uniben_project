from django.shortcuts import render
from rest_framework import generics
from .models import Event
from .serializers import EventSerializer
from django.utils.timezone import now

# All events
class EventListAPI(generics.ListAPIView):
    queryset = Event.objects.all().order_by('start_time')
    serializer_class = EventSerializer

# Upcoming events
class UpcomingEventsAPI(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(start_time__gte=now()).order_by('start_time')

# Past events
class PastEventsAPI(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(end_time__lt=now()).order_by('-start_time')

from .models import Event
from notifications.utils import send_onesignal_notification

def create_event(request):
    event = Event.objects.create(title="Matric Party", date="2025-09-20")
    send_onesignal_notification(
        title="🎉 New Event",
        message=f"{event.title} on {event.date}"
    )
    # continue with your logic...
