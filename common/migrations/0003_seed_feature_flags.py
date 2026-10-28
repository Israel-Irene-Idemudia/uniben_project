from django.db import migrations

# Release 2 and 3 features ship dark (SRS section 3.3, rule 7). Every flag is
# seeded OFF; turning one on is a deliberate admin action.
FLAGS = [
    ("badges", "Full badge catalogue and awards (BE-06, Release 2)"),
    ("friends", "Friend requests, blocks and visibility (BE-12, Release 2)"),
    ("classrooms", "Classrooms and learning rooms (BE-10, Release 2)"),
    ("courses_audio", "Courses, AI explanations and audio (BE-09, Release 2)"),
    ("presence", "Real-time presence in the world (BE-13, Release 3)"),
    (
        "live_location",
        "Opt-in live location sharing (BE-16, Release 3; needs privacy sign-off first)",
    ),
    ("business_discovery", "Business profiles and listings (BE-19, Release 3)"),
]


def seed_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("common", "FeatureFlag")
    for name, description in FLAGS:
        # get_or_create: never overwrites a flag someone already set up.
        FeatureFlag.objects.get_or_create(
            name=name,
            defaults={"description": description, "enabled": False, "audience": "all"},
        )


class Migration(migrations.Migration):
    dependencies = [("common", "0002_featureflag")]

    operations = [migrations.RunPython(seed_flags, migrations.RunPython.noop)]