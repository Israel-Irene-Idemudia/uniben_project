from django.urls import path
from .views import RegisterView, UpdateProfileView, MeView
from .profile_views import (
    TimetableListCreateView,
    TimetableDetailView,
    UserPreferencesView,
    TimetableBulkSyncView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path('me/', MeView.as_view(), name='me'),
    path("profile/update/", UpdateProfileView.as_view(), name="update_profile"),
    
    # Profile sync endpoints
    path('profile/timetable/', TimetableListCreateView.as_view(), name='timetable-list'),
    path('profile/timetable/<int:pk>/', TimetableDetailView.as_view(), name='timetable-detail'),
    path('profile/timetable/bulk-sync/', TimetableBulkSyncView.as_view(), name='timetable-bulk-sync'),
    path('profile/preferences/', UserPreferencesView.as_view(), name='user-preferences'),
]
