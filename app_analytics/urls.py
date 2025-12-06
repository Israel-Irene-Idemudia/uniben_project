from django.urls import path
from .views import AnalyticsView, TrackActivityView

urlpatterns = [
    path('stats/', AnalyticsView.as_view(), name='analytics-stats'),
    path('track/', TrackActivityView.as_view(), name='track-activity'),
]
