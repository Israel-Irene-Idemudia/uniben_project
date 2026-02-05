from django.urls import path
from .views import AnalyticsView, TrackActivityView, StudentBreakdownView

urlpatterns = [
    path('stats/', AnalyticsView.as_view(), name='analytics-stats'),
    path('students-breakdown/', StudentBreakdownView.as_view(),
         name='students-breakdown'),
    path('track/', TrackActivityView.as_view(), name='track-activity'),
]
