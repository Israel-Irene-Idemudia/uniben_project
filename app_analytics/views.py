from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from .models import UserActivity
from cbt.models import ExamSession
from news.models import News
from events.models import Event
from accounts.models import UserProfile
from core.models import Faculty, Department, Level

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

        # Users joined today
        joined_today = User.objects.filter(
            date_joined__date=today
        ).count()

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
            # Active Users
            count = UserActivity.objects.filter(
                timestamp__date=date
            ).values('user').distinct().count()
            # New Joiners
            joiners_count = User.objects.filter(
                date_joined__date=date
            ).count()

            daily_activity.append({
                'date': date.isoformat(),
                'active_users': count,
                'joined_users': joiners_count
            })

        return Response({
            'total_users': total_users,
            'joined_today': joined_today,
            'active_today': active_today,
            'active_week': active_week,
            'total_news': total_news,
            'total_events': total_events,
            'total_quizzes': total_quizzes,
            'feature_usage': list(feature_usage),
            # Reverse to chronological order
            'daily_activity': daily_activity[::-1],
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


class StudentBreakdownView(APIView):
    """
    Get detailed student breakdown by faculty, department, and level.
    Returns statistics for admin analytics.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        try:
            # Get all user profiles
            profiles = UserProfile.objects.select_related(
                'faculty', 'department', 'level')

            # Students by Faculty
            faculty_breakdown = []
            faculties = Faculty.objects.all()
            for faculty in faculties:
                count = profiles.filter(faculty=faculty).count()
                if count > 0:
                    faculty_breakdown.append({
                        'name': faculty.name,
                        'count': count
                    })

            # Students by Department (top 10)
            department_breakdown = []
            departments = Department.objects.all()
            for dept in departments:
                count = profiles.filter(department=dept).count()
                if count > 0:
                    department_breakdown.append({
                        'name': dept.name,
                        'faculty': dept.faculty.name if getattr(dept, 'faculty', None) else 'N/A',
                        'count': count
                    })
            # Sort by count and get top 10
            department_breakdown = sorted(
                department_breakdown,
                key=lambda x: x['count'],
                reverse=True
            )[:10]

            # Students by Level (grouped by numeric level: 100L, 200L, etc.)
            level_breakdown = []
            # Group students by extracting numeric part of level name
            level_groups = {}
            for profile in profiles:
                if getattr(profile, 'level', None) and getattr(profile.level, 'name', None):
                    # Extract numeric part (e.g., "100" from "100L", "100 Level", etc.)
                    level_name = profile.level.name.strip()
                    # Get first 3 digits
                    numeric_part = ''.join(filter(str.isdigit, level_name))[:3]
                    if numeric_part:
                        level_key = f"{numeric_part}L"
                        level_groups[level_key] = level_groups.get(
                            level_key, 0) + 1

            # Sort by numeric value and create breakdown list
            sorted_levels = sorted(level_groups.items(),
                                   key=lambda x: int(x[0][:-1]))
            for level_name, count in sorted_levels:
                level_breakdown.append({
                    'name': level_name,
                    'count': count
                })

            # Students without complete profile
            incomplete_profiles = User.objects.filter(
                Q(userprofile__isnull=True) |
                Q(userprofile__faculty__isnull=True) |
                Q(userprofile__department__isnull=True) |
                Q(userprofile__level__isnull=True)
            ).count()

            return Response({
                'total_students': User.objects.count(),
                'faculty_breakdown': faculty_breakdown,
                'department_breakdown': department_breakdown,
                'level_breakdown': level_breakdown,
                'incomplete_profiles': incomplete_profiles,
            })
        except Exception as e:
            import traceback
            return Response(
                {'error': str(e), 'traceback': traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TodayJoinersView(APIView):
    """
    Get detailed information about users who joined today.
    Returns list of users with their faculty, department, and level.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today = now.date()

        # Get users who joined today with their profiles
        today_users = User.objects.filter(
            date_joined__date=today
        ).select_related('userprofile__faculty', 'userprofile__department', 'userprofile__level')

        joiners_list = []
        for user in today_users:
            profile = user.userprofile if hasattr(
                user, 'userprofile') else None

            joiners_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'faculty': profile.faculty.name if profile and profile.faculty else 'Not set',
                'department': profile.department.name if profile and profile.department else 'Not set',
                'level': profile.level.name if profile and profile.level else 'Not set',
                'date_joined': user.date_joined.isoformat(),
                'is_active': user.is_active,
                'is_staff': user.is_staff,
            })

        # Group by faculty for summary
        faculty_summary = {}
        for user in today_users:
            profile = user.userprofile if hasattr(
                user, 'userprofile') else None
            faculty_name = profile.faculty.name if profile and profile.faculty else 'Not set'
            faculty_summary[faculty_name] = faculty_summary.get(
                faculty_name, 0) + 1

        # Group by department for summary
        department_summary = {}
        for user in today_users:
            profile = user.userprofile if hasattr(
                user, 'userprofile') else None
            dept_name = profile.department.name if profile and profile.department else 'Not set'
            department_summary[dept_name] = department_summary.get(
                dept_name, 0) + 1

        # Group by level for summary
        level_summary = {}
        for user in today_users:
            profile = user.userprofile if hasattr(
                user, 'userprofile') else None
            level_name = profile.level.name if profile and profile.level else 'Not set'
            level_summary[level_name] = level_summary.get(level_name, 0) + 1

        return Response({
            'total_joiners': len(joiners_list),
            'joiners': joiners_list,
            'faculty_summary': faculty_summary,
            'department_summary': department_summary,
            'level_summary': level_summary,
            'date': today.isoformat(),
        })


class UserDetailsView(APIView):
    """
    Get detailed information about a specific user.
    Returns comprehensive user profile data.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, user_id):
        try:
            user = User.objects.select_related(
                'userprofile__faculty',
                'userprofile__department',
                'userprofile__level'
            ).get(id=user_id)

            profile = user.userprofile if hasattr(
                user, 'userprofile') else None

            # Get user activity stats
            activity_count = UserActivity.objects.filter(user=user).count()
            recent_activity = UserActivity.objects.filter(
                user=user).order_by('-timestamp')[:5]

            # Get CBT exam stats
            exam_sessions = ExamSession.objects.filter(user=user)
            total_exams = exam_sessions.count()
            completed_exams = exam_sessions.filter(
                status=ExamSession.STATUS_SUBMITTED).count()

            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,

                # Profile information
                'faculty': {
                    'id': profile.faculty.id if profile and profile.faculty else None,
                    'name': profile.faculty.name if profile and profile.faculty else 'Not set'
                },
                'department': {
                    'id': profile.department.id if profile and profile.department else None,
                    'name': profile.department.name if profile and profile.department else 'Not set'
                },
                'level': {
                    'id': profile.level.id if profile and profile.level else None,
                    'name': profile.level.name if profile and profile.level else 'Not set'
                },

                # Activity statistics
                'activity_stats': {
                    'total_activities': activity_count,
                    'recent_activities': [
                        {
                            'action': activity.action,
                            'timestamp': activity.timestamp.isoformat(),
                            'metadata': activity.metadata
                        }
                        for activity in recent_activity
                    ]
                },

                # Academic statistics
                'academic_stats': {
                    'total_exams_taken': total_exams,
                    'completed_exams': completed_exams,
                    'pending_exams': total_exams - completed_exams,
                }
            }

            return Response(user_data)

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
