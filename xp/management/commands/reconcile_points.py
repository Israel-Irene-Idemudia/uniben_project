"""Reconciliation report for the points -> ledger cutover (BE-04.6).

Read-only: it never writes. `--dry-run` is accepted so the command reads the
same as the plan; there is nothing to apply. Fix real drift with audited
adjustments in admin (XP adjustments), never by editing balances.

For every student with a profile it compares:
  old  = UserProfile.points (the legacy number / current mirror)
  new  = the ledger's spendable balance
and classifies each difference:
  explained   "legacy write after cutover": the ledger holds only the opening
              row, so points moved afterwards (an old container still running,
              or a direct edit).
  UNEXPLAINED anything else, including a student with points but no ledger
              rows (the opening-balance migration did not cover them).
Exit status is an error if any UNEXPLAINED difference exists, so it can gate a
release (Release 1 acceptance: zero unexplained differences).
"""
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum

from accounts.models import UserProfile
from xp.models import XPLedgerEntry


class Command(BaseCommand):
    help = "Compare UserProfile.points with the XP ledger and explain every difference."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Accepted for clarity; this command never writes.")
        parser.add_argument("--csv", dest="csv_path", help="Write every difference to this CSV file.")

    def handle(self, *args, **options):
        ledger = {
            row["user_id"]: row
            for row in XPLedgerEntry.objects.values("user_id").annotate(
                balance=Sum("amount"), rows=Count("id")
            )
        }
        opening = {
            row["user_id"]: row["n"]
            for row in XPLedgerEntry.objects.filter(kind=XPLedgerEntry.KIND_OPENING_BALANCE)
            .values("user_id")
            .annotate(n=Count("id"))
        }

        old_total = new_total = 0
        differences = []
        for user_id, points in UserProfile.objects.values_list("user_id", "points").iterator():
            row = ledger.get(user_id)
            balance = row["balance"] if row else 0
            old_total += points
            new_total += balance
            diff = balance - points
            if diff == 0:
                continue
            only_opening = row is not None and row["rows"] == opening.get(user_id, 0)
            if only_opening:
                explanation = "explained: legacy write after cutover (points moved after the opening balance)"
                unexplained = False
            elif row is None:
                explanation = "UNEXPLAINED: has points but no ledger rows (opening balance missing)"
                unexplained = True
            else:
                explanation = "UNEXPLAINED: ledger and points differ and the ledger has later activity"
                unexplained = True
            differences.append((user_id, points, balance, diff, explanation, unexplained))

        unexplained_count = sum(1 for d in differences if d[5])
        self.stdout.write(f"Old total (UserProfile.points): {old_total}")
        self.stdout.write(f"New total (ledger balance):     {new_total}")
        self.stdout.write(f"Students with a difference:     {len(differences)}")
        self.stdout.write(f"Unexplained differences:        {unexplained_count}")
        for user_id, points, balance, diff, explanation, _ in differences[:200]:
            self.stdout.write(f"  user {user_id}: old {points}, new {balance}, diff {diff:+d} - {explanation}")
        if len(differences) > 200:
            self.stdout.write(f"  ... {len(differences) - 200} more (use --csv for the full list)")

        if options.get("csv_path"):
            with open(options["csv_path"], "w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["user_id", "old_points", "ledger_balance", "difference", "explanation"])
                for user_id, points, balance, diff, explanation, _ in differences:
                    writer.writerow([user_id, points, balance, diff, explanation])

        if unexplained_count:
            raise CommandError(f"{unexplained_count} unexplained difference(s). Do not launch.")
