from django.urls import path
from .views import AnalyticsView, TrackActivityView, StudentBreakdownView, TodayJoinersView, UserDetailsView

urlpatterns = [
    path('stats/', AnalyticsView.as_view(), name='analytics-stats'),
    path('students-breakdown/', StudentBreakdownView.as_view(),
         name='students-breakdown'),
    path('today-joiners/', TodayJoinersView.as_view(),
         name='today-joiners'),
    path('user-details/<int:user_id>/', UserDetailsView.as_view(),
         name='user-details'),
    path('track/', TrackActivityView.as_view(), name='track-activity'),
]
