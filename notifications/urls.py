from django.urls import path
from .views import (
    BroadcastNotificationView,
    AdminSendNotificationView,
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkAsReadView,
    NotificationMarkAllAsReadView,
    NotificationDeleteView,
    NotificationDeleteAllView,
    SupportTicketCreateView,
    SupportTicketListView,
    SupportTicketDetailView,
)

urlpatterns = [
    # Push notifications
    path('broadcast/', BroadcastNotificationView.as_view(),
         name='broadcast-notification'),

    # In-app notifications
    path('in-app/', NotificationListView.as_view(), name='notification-list'),
    path('in-app/send/', AdminSendNotificationView.as_view(),
         name='admin-send-notification'),
    path('in-app/unread-count/', NotificationUnreadCountView.as_view(),
         name='notification-unread-count'),
    path('in-app/<int:pk>/read/', NotificationMarkAsReadView.as_view(),
         name='notification-mark-read'),
    path('in-app/mark-all-read/', NotificationMarkAllAsReadView.as_view(),
         name='notification-mark-all-read'),
    path('in-app/<int:pk>/delete/', NotificationDeleteView.as_view(),
         name='notification-delete'),
    path('in-app/delete-all/', NotificationDeleteAllView.as_view(),
         name='notification-delete-all'),

    # Support tickets
    path('support/create/', SupportTicketCreateView.as_view(),
         name='support-ticket-create'),
    path('support/list/', SupportTicketListView.as_view(),
         name='support-ticket-list'),
    path('support/<int:pk>/', SupportTicketDetailView.as_view(),
         name='support-ticket-detail'),
]
