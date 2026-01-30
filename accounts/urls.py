from django.urls import path
from .views import RegisterView, UpdateProfileView, MeView, UserListView, UserDetailView, DeleteAccountAPI, AdminDeletionRequestListAPI, AdminDeletionActionAPI
from .profile_views import (
    TimetableListCreateView,
    TimetableDetailView,
    UserPreferencesView,
    TimetableBulkSyncView,
    TodoListCreateView,
    TodoDetailView,
    TodoBulkSyncView,
    # New sync views
    NotesListView,
    NotesBulkSyncView,
    GpaListView,
    GpaBulkSyncView,
    DebaterProgressView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path('me/', MeView.as_view(), name='me'),
    path("profile/update/", UpdateProfileView.as_view(), name="update_profile"),
    path("delete/", DeleteAccountAPI.as_view(), name="delete_account"),
    
    # Timetable sync endpoints
    path('profile/timetable/', TimetableListCreateView.as_view(), name='timetable-list'),
    path('profile/timetable/<int:pk>/', TimetableDetailView.as_view(), name='timetable-detail'),
    path('profile/timetable/bulk-sync/', TimetableBulkSyncView.as_view(), name='timetable-bulk-sync'),
    
    # Todo sync endpoints
    path('profile/todos/', TodoListCreateView.as_view(), name='todo-list'),
    path('profile/todos/<int:pk>/', TodoDetailView.as_view(), name='todo-detail'),
    path('profile/todos/bulk-sync/', TodoBulkSyncView.as_view(), name='todo-bulk-sync'),
    
    # Notes sync endpoints
    path('profile/notes/', NotesListView.as_view(), name='notes-list'),
    path('profile/notes/bulk-sync/', NotesBulkSyncView.as_view(), name='notes-bulk-sync'),
    
    # GPA sync endpoints
    path('profile/gpa/', GpaListView.as_view(), name='gpa-list'),
    path('profile/gpa/bulk-sync/', GpaBulkSyncView.as_view(), name='gpa-bulk-sync'),
    
    # Debater progress sync endpoint
    path('profile/debater/', DebaterProgressView.as_view(), name='debater-progress'),
    
    # User preferences
    path('profile/preferences/', UserPreferencesView.as_view(), name='user-preferences'),
    
    # User management (admin only)
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
    
    # Account Deletion Requests (Admin)
    path('deletion-requests/', AdminDeletionRequestListAPI.as_view(), name='deletion-request-list'),
    path('deletion-requests/<int:pk>/action/', AdminDeletionActionAPI.as_view(), name='deletion-request-action'),
]
