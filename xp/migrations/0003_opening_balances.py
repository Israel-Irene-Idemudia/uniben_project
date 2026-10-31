"""Move every student's existing points into the ledger (BE-04.6).

One `opening_balance` row per student whose UserProfile.points > 0, key
`opening_balance:<user_id>`.

SAFE TO RE-RUN: the unique (user, idempotency_key) constraint plus
ignore_conflicts means a second run adds nothing. Batched (500 at a time).

REVERSIBLE: the reverse step deletes only rows this migration wrote
(kind=opening_balance, source_feature=migration), and REFUSES to run if any
other ledger activity exists, because deleting an opening balance after
students have earned or spent would corrupt balances. It works because
migrations use historical models, which do not carry the ledger's
immutability guards.

DECISION (D-2): points already had past redemptions subtracted, so a
student's opening balance = their current points = their starting lifetime
XP. Past spending is invisible to the ledger. Nobody's level drops.

This runs on deploy against production. Rehearse it first on a restored copy
and run `python manage.py reconcile_points` (see docs/design/xp-ledger.md).
"""
from django.db import migrations

BATCH = 500
SOURCE = "migration"


def forwards(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    XPLedgerEntry = apps.get_model("xp", "XPLedgerEntry")

    last_pk = 0
    while True:
        rows = list(
            UserProfile.objects.filter(points__gt=0, pk__gt=last_pk)
            .order_by("pk")
            .values_list("pk", "user_id", "points")[:BATCH]
        )
        if not rows:
            break
        XPLedgerEntry.objects.bulk_create(
            [
                XPLedgerEntry(
                    user_id=user_id,
                    amount=points,
                    kind="opening_balance",
                    reason_code="opening_balance",
                    source_feature=SOURCE,
                    source_record_id=str(user_id),
                    idempotency_key=f"opening_balance:{user_id}",
                    metadata={"from": "UserProfile.points"},
                )
                for _pk, user_id, points in rows
            ],
            ignore_conflicts=True,
        )
        last_pk = rows[-1][0]


def backwards(apps, schema_editor):
    XPLedgerEntry = apps.get_model("xp", "XPLedgerEntry")
    ours = XPLedgerEntry.objects.filter(kind="opening_balance", source_feature=SOURCE)
    if XPLedgerEntry.objects.exclude(pk__in=ours.values("pk")).exists():
        raise RuntimeError(
            "Refusing to reverse opening balances: the ledger already has other activity. "
            "Restore from a backup instead."
        )
    ours.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("xp", "0002_seed_rules_and_levels"),
        # UserProfile.points exists from the first accounts migrations; 0009 is
        # the newest one this migration needs.
        ("accounts", "0009_userprofile_matric_number_userprofile_student_id"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
