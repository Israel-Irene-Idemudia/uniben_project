from django.db import transaction
from django.utils import timezone

from accounts.models import StudentDepartmentHistory


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