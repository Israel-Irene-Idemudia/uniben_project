from django.utils.timezone import now
from rest_framework import generics, permissions
from .models import Event
from .serializers import EventSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit/delete.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions only for staff users
        return request.user and request.user.is_staff


# All events (now with create for admins)
class EventListAPI(generics.ListCreateAPIView):
    queryset = Event.objects.all().order_by('event_date')
    serializer_class = EventSerializer
    permission_classes = [IsAdminOrReadOnly]
    
    def perform_create(self, serializer):
        # Save event (creator field is optional in Event model)
        serializer.save()



# Event detail (update/delete for admins)
class EventDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAdminOrReadOnly]


# Upcoming events (read-only)
class UpcomingEventsAPI(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(event_date__gte=now()).order_by('event_date')


# Past events (read-only)
class PastEventsAPI(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        return Event.objects.filter(event_date__lt=now()).order_by('-event_date')
