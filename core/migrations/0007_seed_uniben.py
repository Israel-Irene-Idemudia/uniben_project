"""Seed UNIBEN and attach every existing faculty to it.

Idempotent: get_or_create, and only faculties with NO university are touched,
so re-running it (or running it after an admin assigned faculties elsewhere)
changes nothing. No student row is read or written: students reach their
university through profile.faculty.

Reverse is a deliberate no-op: the schema migration's reverse drops the
column and table, and a data rollback must never guess which links an admin
made by hand.
"""
from django.db import migrations

UNIBEN = {"code": "uniben", "name": "University of Benin", "short_name": "UNIBEN"}


def seed(apps, schema_editor):
    University = apps.get_model("core", "University")
    Faculty = apps.get_model("core", "Faculty")
    uniben, _ = University.objects.get_or_create(
        code=UNIBEN["code"],
        defaults={"name": UNIBEN["name"], "short_name": UNIBEN["short_name"]},
    )
    Faculty.objects.filter(university__isnull=True).update(university=uniben)


class Migration(migrations.Migration):
    dependencies = [("core", "0006_university_faculty_university")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
