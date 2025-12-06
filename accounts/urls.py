from django.urls import path
from .views import RegisterView, UpdateProfileView, MeView, UserListView, UserDetailView
from .profile_views import (
    TimetableListCreateView,
    TimetableDetailView,
    UserPreferencesView,
    TimetableBulkSyncView,
    TodoListCreateView,
    TodoDetailView,
    TodoBulkSyncView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path('me/', MeView.as_view(), name='me'),
    path("profile/update/", UpdateProfileView.as_view(), name="update_profile"),
    
    # Timetable sync endpoints
    path('profile/timetable/', TimetableListCreateView.as_view(), name='timetable-list'),
    path('profile/timetable/<int:pk>/', TimetableDetailView.as_view(), name='timetable-detail'),
    path('profile/timetable/bulk-sync/', TimetableBulkSyncView.as_view(), name='timetable-bulk-sync'),
    
    # Todo sync endpoints
    path('profile/todos/', TodoListCreateView.as_view(), name='todo-list'),
    path('profile/todos/<int:pk>/', TodoDetailView.as_view(), name='todo-detail'),
    path('profile/todos/bulk-sync/', TodoBulkSyncView.as_view(), name='todo-bulk-sync'),
    
    # User preferences
    path('profile/preferences/', UserPreferencesView.as_view(), name='user-preferences'),
    
    # User management (admin only)
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
]
