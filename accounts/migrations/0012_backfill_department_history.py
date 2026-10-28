from django.db import migrations

BACKFILL_REASON = "Backfill (Phase 2.3)"
BATCH = 500


def backfill(apps, schema_editor):
    """One open history row per profile that has a department.

    Defensive on purpose (this runs on the live database at startup): it never
    raises on odd data, skips students who already have an open row, and uses
    ignore_conflicts so a re-run cannot fail on the one-open-row constraint.
    """
    Profile = apps.get_model("accounts", "UserProfile")
    History = apps.get_model("accounts", "StudentDepartmentHistory")

    already = set(
        History.objects.filter(effective_to__isnull=True).values_list("user_id", flat=True)
    )
    profiles = (
        Profile.objects.filter(department__isnull=False)
        .select_related("user", "department", "department__faculty")
        .order_by("pk")
    )
    batch = []
    for profile in profiles.iterator(chunk_size=BATCH):
        if profile.user_id in already:
            continue
        department = profile.department
        faculty = department.faculty
        batch.append(
            History(
                user_id=profile.user_id,
                faculty_id=faculty.pk if faculty else None,
                department_id=department.pk,
                faculty_name=faculty.name if faculty else "",
                department_name=department.name,
                effective_from=profile.user.date_joined,
                reason=BACKFILL_REASON,
            )
        )
        if len(batch) >= BATCH:
            History.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        History.objects.bulk_create(batch, ignore_conflicts=True)


def undo(apps, schema_editor):
    apps.get_model("accounts", "StudentDepartmentHistory").objects.filter(
        reason=BACKFILL_REASON
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0011_studentdepartmenthistory")]
    operations = [migrations.RunPython(backfill, undo)]