"""Opening-balance migration and the reconcile_points report (BE-04.6)."""
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase
import importlib

from accounts.models import UserProfile
from xp.models import XPLedgerEntry
from xp.services import award_xp, get_balance

from .helpers import make_student

MIGRATION = importlib.import_module("xp.migrations.0003_opening_balances")


def historical_apps():
    loader = MigrationLoader(connection)
    return MigrationExecutor(connection).loader.project_state([("xp", "0003_opening_balances")]).apps


def legacy_student(name, points):
    user = make_student(name)
    UserProfile.objects.filter(user=user).update(points=points)  # the old way: only the integer
    return user


class OpeningBalanceTests(TestCase):
    def setUp(self):
        self.a = legacy_student("a", 70)
        self.b = legacy_student("b", 5)
        self.zero = legacy_student("z", 0)

    def test_writes_one_row_per_student_with_points_and_is_idempotent(self):
        MIGRATION.forwards(historical_apps(), None)
        MIGRATION.forwards(historical_apps(), None)  # second run adds nothing
        self.assertEqual(XPLedgerEntry.objects.filter(kind="opening_balance").count(), 2)
        self.assertEqual(get_balance(self.a), 70)
        self.assertEqual(get_balance(self.b), 5)
        self.assertEqual(XPLedgerEntry.objects.filter(user=self.zero).count(), 0)

    def test_reverse_removes_only_its_own_rows(self):
        MIGRATION.forwards(historical_apps(), None)
        MIGRATION.backwards(historical_apps(), None)
        self.assertEqual(XPLedgerEntry.objects.count(), 0)

    def test_reverse_refuses_once_the_ledger_has_other_activity(self):
        MIGRATION.forwards(historical_apps(), None)
        award_xp(self.a, action_code="material_verified", source_feature="materials", source_record_id="1")
        with self.assertRaises(RuntimeError):
            MIGRATION.backwards(historical_apps(), None)
        self.assertEqual(XPLedgerEntry.objects.filter(kind="opening_balance").count(), 2)


class ReconcileTests(TestCase):
    def run_report(self):
        out = StringIO()
        try:
            call_command("reconcile_points", "--dry-run", stdout=out)
            failed = False
        except CommandError:
            failed = True
        return out.getvalue(), failed

    def test_clean_cutover_has_zero_differences(self):
        legacy_student("a", 70)
        legacy_student("b", 5)
        MIGRATION.forwards(historical_apps(), None)
        text, failed = self.run_report()
        self.assertFalse(failed, text)
        self.assertIn("Unexplained differences:        0", text)
        self.assertIn("Old total (UserProfile.points): 75", text)
        self.assertIn("New total (ledger balance):     75", text)

    def test_legacy_write_after_cutover_is_explained_not_fatal(self):
        user = legacy_student("a", 70)
        MIGRATION.forwards(historical_apps(), None)
        UserProfile.objects.filter(user=user).update(points=80)  # old container wrote +10
        text, failed = self.run_report()
        self.assertFalse(failed, text)
        self.assertIn("explained: legacy write after cutover", text)

    def test_student_with_points_but_no_ledger_rows_is_unexplained(self):
        legacy_student("a", 70)  # migration NOT run
        text, failed = self.run_report()
        self.assertTrue(failed)
        self.assertIn("UNEXPLAINED", text)
