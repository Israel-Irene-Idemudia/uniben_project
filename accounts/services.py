import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from accounts.models import DepartmentChangeApproval, StudentDepartmentHistory, UserProfile
from common.services import get_setting, log_audit

logger = logging.getLogger(__name__)

LAGOS = ZoneInfo("Africa/Lagos")
FALLBACK_DAYS = 180  # used until academic.semester_* settings exist (D-3)
BACKFILL_REASON = "Backfill (Phase 2.3)"  # same text as migration 0012
CHANGE_REASON = "Department change"


class DepartmentChangeError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def sync_department_history(profile, *, changed_by=None, reason=""):
    """Make the history match the profile's current department.

    Closes the open row and opens a new one only when the department really
    changed. Safe to call repeatedly. Returns the current open row or None.
    """
    now = timezone.now()
    with transaction.atomic():
        # select_for_update: no-op on SQLite, serialises changes on PostgreSQL.
        open_row = (
            StudentDepartmentHistory.objects.select_for_update()
            .filter(user_id=profile.user_id, effective_to__isnull=True)
            .first()
        )
        if open_row is not None and open_row.department_id == profile.department_id:
            return open_row
        if open_row is not None:
            open_row.effective_to = now
            open_row.save(update_fields=["effective_to"])
        if profile.department_id is None:
            return None
        department = profile.department
        faculty = department.faculty
        return StudentDepartmentHistory.objects.create(
            user_id=profile.user_id,
            faculty=faculty,
            department=department,
            faculty_name=faculty.name,
            department_name=department.name,
            effective_from=now,
            changed_by=changed_by,
            reason=reason or "Profile update",
        )


def semester_window_start(now):
    """Start of the current semester window (D-3).

    Uses the admin-editable settings academic.semester_start / _end (ISO
    dates, Africa/Lagos). Falls back to the last FALLBACK_DAYS days when they
    are missing, invalid, or today is outside them.
    """
    try:
        start = date.fromisoformat(get_setting("academic.semester_start"))
        end = date.fromisoformat(get_setting("academic.semester_end"))
    except (TypeError, ValueError):
        start = end = None
    today = now.astimezone(LAGOS).date()
    if start and end and start <= today <= end:
        return datetime.combine(start, time.min, tzinfo=LAGOS)
    return now - timedelta(days=FALLBACK_DAYS)


def _changes_since(user, since):
    """Real department changes since `since`.

    The student's first-ever history row is the initial choice, not a change,
    and backfilled rows are guesses, so neither counts.
    """
    first = (
        StudentDepartmentHistory.objects.filter(user=user).order_by("effective_from", "id").first()
    )
    rows = StudentDepartmentHistory.objects.filter(user=user, effective_from__gte=since).exclude(
        reason=BACKFILL_REASON
    )
    if first is not None:
        rows = rows.exclude(pk=first.pk)
    return rows.count()


def _snapshot(profile):
    return {
        "faculty_id": profile.faculty_id,
        "department_id": profile.department_id,
        "level_id": profile.level_id,
    }


@transaction.atomic
def change_department(user, department, level=None, *, reason=""):
    """Move a student to `department`, enforcing once per semester.

    Writes history and the audit row in the same transaction. Never touches
    past history or past results.
    """
    # of=("self",): PostgreSQL refuses FOR UPDATE across the nullable joins
    # that select_related adds, so lock only the profile row.
    profile = (
        UserProfile.objects.select_for_update(of=("self",))
        .select_related("faculty", "department", "level")
        .get(user=user)
    )
    if profile.department_id == department.id:
        raise DepartmentChangeError("same_department", "You are already in this department.")

    now = timezone.now()
    approval = None
    if profile.department_id is not None and _changes_since(user, semester_window_start(now)) > 0:
        approval = (
            DepartmentChangeApproval.objects.select_for_update()
            .filter(user=user, used_at__isnull=True)
            .order_by("created_at", "id")
            .first()
        )
        if approval is None:
            raise DepartmentChangeError(
                "limit_reached",
                "You have already changed department this semester. "
                "Ask an admin to approve another change.",
            )

    before = _snapshot(profile)
    profile.faculty = department.faculty
    profile.department = department
    profile.level = level
    profile.course_area = level.course_area if level is not None else None

    # History first, then save: the post_save signal then finds the open row
    # already matching and does nothing, so there is exactly one new row.
    sync_department_history(profile, changed_by=user, reason=CHANGE_REASON)
    profile.save()

    if approval is not None:
        approval.used_at = now
        approval.save(update_fields=["used_at"])

    log_audit(
        actor=user,
        action="department.change",
        target_type="UserProfile",
        target_id=profile.pk,
        before=before,
        after=_snapshot(profile),
        reason=reason or "Student request",
    )
    return profile