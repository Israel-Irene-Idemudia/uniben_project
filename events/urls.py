from django.urls import path
from .views import EventListAPI, UpcomingEventsAPI, PastEventsAPI

urlpatterns = [
    path('events/', EventListAPI.as_view(), name='events-list'),
    path('events/upcoming/', UpcomingEventsAPI.as_view(), name='upcoming-events'),
    path('events/past/', PastEventsAPI.as_view(), name='past-events'),
]
