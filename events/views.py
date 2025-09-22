from django.utils.timezone import now
from rest_framework import generics
from .models import Event
from .serializers import EventSerializer

# All events
class EventListAPI(generics.ListAPIView):
    queryset = Event.objects.all().order_by('event_date')
    serializer_class = EventSerializer

# Upcoming events
class UpcomingEventsAPI(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(event_date__gte=now()).order_by('event_date')

# Past events
class PastEventsAPI(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(event_date__lt=now()).order_by('-event_date')
