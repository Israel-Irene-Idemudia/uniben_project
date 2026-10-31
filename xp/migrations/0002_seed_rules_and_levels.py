"""Seed XP rules and the level curve (D-12). Data only, editable in admin.

DECISION (D-12): conservative starting values, chosen by the build, to be
tuned by Israel in admin with no deploy. material_verified keeps the old +10
behaviour. The other rules are not called by any code until Phases 4 and 5;
they exist so those phases only have to call award_xp.

Idempotent: re-running changes nothing, and it never overwrites a row an
admin has already edited (get_or_create). Reverse is a deliberate no-op so a
rollback cannot delete admin-edited configuration.
"""
from datetime import datetime, timezone

from django.db import migrations

RULES = [
    # action_code, amount, daily_cap, diminishing_after, diminishing_percent, description
    ("material_verified", 10, 50, None, 50, "An admin verified a student's uploaded material (the old +10 points)."),
    ("past_questions_practice", 5, 25, 3, 50, "Finished a Past Questions practice session (Phase 5)."),
    ("past_questions_competitive", 15, 45, None, 50, "Finished a timed competitive Past Questions session (Phase 5)."),
    ("quest_complete", 10, 100, None, 50, "Completed a quest. Callers pass the quest's own reward (Phase 4)."),
    ("course_section_complete", 5, 25, 3, 50, "Completed a course section (Release 2)."),
]

LEVELS = [
    (1, 0, "Fresher"),
    (2, 100, "Learner"),
    (3, 250, "Scholar"),
    (4, 500, "Achiever"),
    (5, 900, "Honours"),
    (6, 1400, "Distinction"),
    (7, 2000, "First Class"),
    (8, 2800, "Dean's List"),
    (9, 3800, "Professor"),
    (10, 5000, "Legend"),
]

CURVE_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def seed(apps, schema_editor):
    XPRule = apps.get_model("xp", "XPRule")
    LevelConfig = apps.get_model("xp", "LevelConfig")
    for code, amount, cap, dim_after, dim_pct, desc in RULES:
        XPRule.objects.get_or_create(
            action_code=code,
            defaults={
                "amount": amount,
                "daily_cap": cap,
                "diminishing_after": dim_after,
                "diminishing_percent": dim_pct,
                "description": desc,
            },
        )
    for level, threshold, title in LEVELS:
        LevelConfig.objects.get_or_create(
            level=level,
            effective_from=CURVE_START,
            defaults={"xp_threshold": threshold, "title": title},
        )


class Migration(migrations.Migration):
    dependencies = [("xp", "0001_xp_ledger")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
