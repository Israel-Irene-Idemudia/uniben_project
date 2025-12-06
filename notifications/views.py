from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import send_onesignal_notification


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class BroadcastNotificationView(APIView):
    """
    Send a broadcast push notification to all app users.
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
            result = send_onesignal_notification(title, body)
            
            if 'error' in result:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                'success': True,
                'message': 'Notification sent successfully',
                'onesignal_response': result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
