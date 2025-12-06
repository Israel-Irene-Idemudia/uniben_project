from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from .models import UserActivity
from cbt.models import ExamSession
from news.models import News
from events.models import Event

User = get_user_model()


class IsAdminUser(permissions.BasePermission):
    """Only allow admin users"""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class AnalyticsView(APIView):
    """
    Get analytics data for admin dashboard.
    Returns user stats, feature usage, and daily activity trends.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        
        # User stats
        total_users = User.objects.count()
        active_today = UserActivity.objects.filter(
            timestamp__date=today
        ).values('user').distinct().count()
        
        active_week = UserActivity.objects.filter(
            timestamp__gte=week_ago
        ).values('user').distinct().count()
        
        # Content stats
        total_news = News.objects.count()
        total_events = Event.objects.count()
        total_quizzes = ExamSession.objects.filter(
            status=ExamSession.STATUS_SUBMITTED
        ).count()
        
        # Feature usage (last 7 days)
        feature_usage = UserActivity.objects.filter(
            timestamp__gte=week_ago
        ).values('action').annotate(count=Count('id')).order_by('-count')
        
        # Daily activity trend (last 7 days)
        daily_activity = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = UserActivity.objects.filter(
                timestamp__date=date
            ).values('user').distinct().count()
            daily_activity.append({
                'date': date.isoformat(),
                'active_users': count
            })
        
        return Response({
            'total_users': total_users,
            'active_today': active_today,
            'active_week': active_week,
            'total_news': total_news,
            'total_events': total_events,
            'total_quizzes': total_quizzes,
            'feature_usage': list(feature_usage),
            'daily_activity': daily_activity[::-1],  # Reverse to chronological order
        })


class TrackActivityView(APIView):
    """
    Track user activity.
    POST with action type to log user activity.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        action = request.data.get('action')
        metadata = request.data.get('metadata', {})
        
        if not action:
            return Response(
                {'error': 'Action is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate action
        valid_actions = [choice[0] for choice in UserActivity.ACTION_CHOICES]
        if action not in valid_actions:
            return Response(
                {'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            action=action,
            metadata=metadata
        )
        
        return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
