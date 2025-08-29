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

