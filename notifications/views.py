from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .utils import send_onesignal_notification
from .models import InAppNotification, SupportTicket
from .serializers import (
    InAppNotificationSerializer,
    SupportTicketSerializer,
    SupportTicketCreateSerializer
)


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class BroadcastNotificationView(APIView):
    """
    Send a broadcast push notification to all app users.
    Also creates in-app notifications for all users.
    Only accessible by admin users.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request):
        title = request.data.get('title')
        body = request.data.get('body')

        if not title or not body:
            return Response(
                {'error': 'Both title and body are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Send push notification via OneSignal
            result = send_onesignal_notification(title, body)

            if 'error' in result:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Create in-app notifications for all users
            from accounts.models import User
            users = User.objects.all()

            notifications_created = 0
            for user in users:
                InAppNotification.objects.create(
                    user=user,
                    notification_type='announcement',
                    title=title,
                    message=body,
                )
                notifications_created += 1

            return Response({
                'success': True,
                'message': 'Notification sent successfully',
                'onesignal_response': result,
                'in_app_notifications_created': notifications_created
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ==================== IN-APP NOTIFICATIONS ====================

class AdminSendNotificationView(APIView):
    """
    Admin endpoint to send in-app notification to a specific user.
    Used for direct messaging from admin panel.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request):
        user_id = request.data.get('user_id')
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('notification_type', 'general')

        if not all([user_id, title, message]):
            return Response(
                {'error': 'user_id, title, and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from accounts.models import User
            user = User.objects.get(id=user_id)

            notification = InAppNotification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
            )

            serializer = InAppNotificationSerializer(notification)
            return Response(
                {'success': True, 'notification': serializer.data},
                status=status.HTTP_201_CREATED
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotificationListView(generics.ListAPIView):
    """
    Get all notifications for the authenticated user.
    Supports filtering: ?is_read=true/false
    """
    serializer_class = InAppNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = InAppNotification.objects.filter(user=self.request.user)

        # Filter by read status if provided
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)

        return queryset


class NotificationUnreadCountView(APIView):
    """
    Get count of unread notifications for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = InAppNotification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})


class NotificationMarkAsReadView(APIView):
    """
    Mark a notification as read.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = InAppNotification.objects.get(
                pk=pk,
                user=request.user
            )
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()

            serializer = InAppNotificationSerializer(notification)
            return Response(serializer.data)
        except InAppNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class NotificationMarkAllAsReadView(APIView):
    """
    Mark all notifications as read for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated_count = InAppNotification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'updated_count': updated_count})


class NotificationDeleteView(APIView):
    """
    Delete a notification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            notification = InAppNotification.objects.get(
                pk=pk,
                user=request.user
            )
            notification.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except InAppNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class NotificationDeleteAllView(APIView):
    """
    Delete all notifications for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        deleted_count = InAppNotification.objects.filter(
            user=request.user
        ).delete()[0]
        return Response(
            {'deleted_count': deleted_count},
            status=status.HTTP_200_OK
        )


# ==================== SUPPORT TICKETS ====================

class SupportTicketCreateView(generics.CreateAPIView):
    """
    Create a new support ticket (replaces the old contact us endpoint).
    """
    serializer_class = SupportTicketCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SupportTicketListView(generics.ListAPIView):
    """
    List support tickets (Admin only).
    Supports filtering: ?status=pending/in_progress/resolved/closed
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        queryset = SupportTicket.objects.all()

        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset


class SupportTicketDetailView(generics.RetrieveUpdateAPIView):
    """
    Get or update a support ticket (Admin only).
    Used for admins to reply to tickets.
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    queryset = SupportTicket.objects.all()

    def perform_update(self, serializer):
        # If admin is adding a reply, create an in-app notification for the user
        admin_reply = self.request.data.get('admin_reply')
        ticket = serializer.instance

        if admin_reply and admin_reply != ticket.admin_reply:
            # Update ticket with reply info
            serializer.save(
                replied_by=self.request.user,
                replied_at=timezone.now()
            )

            # Create in-app notification for the user
            InAppNotification.objects.create(
                user=ticket.user,
                notification_type='support_reply',
                title=f'Reply to: {ticket.subject}',
                message=admin_reply,
                related_id=ticket.id,
                related_type='support_ticket'
            )
        else:
            serializer.save()
