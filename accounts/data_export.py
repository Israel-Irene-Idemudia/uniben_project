"""A student's own data, as one JSON-friendly dict (BE-01.6)."""
from django.utils import timezone

from accounts.models import (
    AuthEvent,
    StudentDepartmentHistory,
    UserDebaterProgress,
    UserGpaEntry,
    UserNoteEntry,
    UserPreferences,
    UserProfile,
    UserTimetableEntry,
    UserTodoEntry,
)
from rewards.models import Redemption


def _rows(queryset, fields):
    return list(queryset.values(*fields))


def export_user_data(user):
    profile = UserProfile.objects.select_related("faculty", "department", "level").filter(user=user).first()
    prefs = UserPreferences.objects.filter(user=user).first()
    debater = UserDebaterProgress.objects.filter(user=user).first()
    return {
        "generated_at": timezone.now(),
        "account": {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "date_joined": user.date_joined,
        },
        "profile": None
        if profile is None
        else {
            "faculty": profile.faculty.name if profile.faculty else None,
            "department": profile.department.name if profile.department else None,
            "academic_level": profile.level.name if profile.level else None,
            "phone": profile.phone,
            "network": profile.network,
            "student_id": profile.student_id,
            "matric_number": profile.matric_number,
            "points": profile.points,
        },
        "department_history": _rows(
            StudentDepartmentHistory.objects.filter(user=user).order_by("effective_from"),
            ["faculty_name", "department_name", "effective_from", "effective_to", "reason"],
        ),
        "preferences": None
        if prefs is None
        else {
            "notifications_enabled": prefs.notifications_enabled,
            "notification_sound": prefs.notification_sound,
            "theme": prefs.theme,
            "other_settings": prefs.other_settings,
        },
        "timetable": _rows(
            UserTimetableEntry.objects.filter(user=user),
            ["subject", "day", "time", "alarm_enabled", "alarm_times"],
        ),
        "todos": _rows(
            UserTodoEntry.objects.filter(user=user), ["task", "time", "is_completed", "created_at"]
        ),
        "notes": _rows(
            UserNoteEntry.objects.filter(user=user),
            ["note_id", "title", "body", "color", "pinned", "note_updated_at"],
        ),
        "gpa": _rows(
            UserGpaEntry.objects.filter(user=user),
            ["course_code", "course_name", "unit", "grade", "grade_point"],
        ),
        "debater_progress": None
        if debater is None
        else {
            "beginner_score": debater.beginner_score,
            "intermediate_score": debater.intermediate_score,
            "advanced_score": debater.advanced_score,
            "expert_score": debater.expert_score,
        },
        "redemptions": _rows(
            Redemption.objects.filter(user=user),
            ["reward_type", "point_cost", "phone", "network", "status", "created_at"],
        ),
        "login_events": _rows(
            AuthEvent.objects.filter(user=user, kind=AuthEvent.KIND_LOGIN).order_by("-created_at")[:50],
            ["created_at", "success", "detail", "ip_address"],
        ),
    }