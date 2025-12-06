from django.urls import path
from .views import BroadcastNotificationView

urlpatterns = [
    path('broadcast/', BroadcastNotificationView.as_view(), name='broadcast-notification'),
]
