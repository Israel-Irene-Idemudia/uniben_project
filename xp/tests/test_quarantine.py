"""Phase 4.5 quarantine record (BE-05.5, D-22): who may quarantine, the
mandatory reason, the audit row, idempotency, immutability of both the
quarantine record and the original ledger row, and the admin entry point.
No public API exists for quarantine."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import get_resolver, reverse

from common.models import AuditLog, ImmutableRecordError
from xp.models import XPLedgerEntry, XPQuarantine, XPRule
from xp.quarantine import (
    QuarantineError,
    QuarantinePermissionDenied,
    is_quarantined,
    quarantine_award,
)
from xp.services import adjust_xp, award_xp, get_balance, get_level, get_lifetime_xp, spend_points

from .helpers import make_admin, make_student

User = get_user_model()


def make_staff(username, *perms):
    user = User.objects.create_user(username=username, password="pass12345", is_staff=True)
    for codename in perms:
        user.user_permissions.add(Permission.objects.get(content_type__app_label="xp", codename=codename))
    return User.objects.get(pk=user.pk)  # fresh instance: no stale permission cache


class QuarantineTestBase(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student("stu")
        XPRule.objects.get_or_create(action_code="test_action", defaults={"amount": 10})
        self.award = award_xp(
            self.student, action_code="test_action", source_feature="t", source_record_id="1",
        ).entry


class QuarantineServiceTests(QuarantineTestBase):
    def test_superuser_quarantines_with_reason_and_audit(self):
        record = quarantine_award(self.award, actor=self.admin, reason="  Impossible time  ")
        self.assertEqual(
            (record.entry_id, record.state, record.reason, record.flagged_by, record.source),
            (self.award.pk, XPQuarantine.STATE_QUARANTINED, "Impossible time", self.admin, "manual"),
        )
        self.assertTrue(is_quarantined(self.award))
        log = AuditLog.objects.get(action="xp.quarantine")
        self.assertEqual((log.actor, log.target_type, log.target_id), (self.admin, "XPLedgerEntry", str(self.award.pk)))
        self.assertEqual(log.reason, "Impossible time")
        self.assertEqual(log.before, {"quarantined": False})
        self.assertEqual(log.after["quarantine_id"], record.pk)
        self.assertEqual((log.after["user_id"], log.after["amount"]), (self.student.pk, 10))

    def test_staff_with_the_permission_can_quarantine(self):
        mod = make_staff("mod", "quarantine_xp_award")
        quarantine_award(self.award, actor=mod, reason="Repeated identical sessions")
        self.assertTrue(is_quarantined(self.award))

    def test_unauthorised_actors_are_refused_and_nothing_is_written(self):
        actors = {
            "student": self.student,
            "staff without permission": make_staff("plain"),
            "staff with view only": make_staff("viewer", "view_xpquarantine"),
            "inactive holder": User.objects.create_superuser("old", "o@t.com", "x", is_active=False),
            "no actor": None,
        }
        for label, actor in actors.items():
            with self.subTest(actor=label), self.assertRaises(QuarantinePermissionDenied):
                quarantine_award(self.award, actor=actor, reason="r")
        self.assertFalse(XPQuarantine.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action="xp.quarantine").exists())

    def test_reason_is_mandatory(self):
        for reason in ("", "   ", None):
            with self.subTest(reason=reason), self.assertRaises(QuarantineError):
                quarantine_award(self.award, actor=self.admin, reason=reason)
        self.assertFalse(XPQuarantine.objects.exists())

    def test_only_award_rows_can_be_quarantined(self):
        adjustment = adjust_xp(self.student, amount=50, reason="r", actor=self.admin, idempotency_key="a1")
        spend = spend_points(self.student, cost=5, reason_code="reward", source_feature="t", idempotency_key="s1")
        for entry in (adjustment, spend):
            with self.subTest(kind=entry.kind), self.assertRaises(QuarantineError):
                quarantine_award(entry, actor=self.admin, reason="r")
        self.assertFalse(XPQuarantine.objects.exists())

    def test_quarantining_twice_is_idempotent(self):
        first = quarantine_award(self.award, actor=self.admin, reason="one")
        again = quarantine_award(self.award, actor=self.admin, reason="two")
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(XPQuarantine.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="xp.quarantine").count(), 1)

    def test_one_open_case_per_award_is_enforced_by_the_database(self):
        quarantine_award(self.award, actor=self.admin, reason="one")
        with self.assertRaises(IntegrityError), transaction.atomic():
            XPQuarantine.objects.create(entry=self.award, reason="dup", flagged_by=self.admin)


class ImmutabilityTests(QuarantineTestBase):
    def test_original_ledger_row_is_unchanged(self):
        before = XPLedgerEntry.objects.filter(pk=self.award.pk).values().get()
        rows = XPLedgerEntry.objects.count()
        quarantine_award(self.award, actor=self.admin, reason="r")
        self.assertEqual(XPLedgerEntry.objects.filter(pk=self.award.pk).values().get(), before)
        self.assertEqual(XPLedgerEntry.objects.count(), rows)

    def test_balance_lifetime_xp_and_level_are_unchanged(self):
        # D-2 is untouched: quarantine excludes from boards only (BE-05.5).
        before = (get_balance(self.student), get_lifetime_xp(self.student), get_level(self.student))
        quarantine_award(self.award, actor=self.admin, reason="r")
        after = (get_balance(self.student), get_lifetime_xp(self.student), get_level(self.student))
        self.assertEqual(after, before)

    def test_quarantine_record_cannot_be_changed_or_deleted(self):
        record = quarantine_award(self.award, actor=self.admin, reason="r")
        record.reason = "tampered"
        with self.assertRaises(ImmutableRecordError):
            record.save()
        with self.assertRaises(ImmutableRecordError):
            record.delete()
        with self.assertRaises(ImmutableRecordError):
            XPQuarantine.objects.all().update(state=XPQuarantine.STATE_CLEARED)
        with self.assertRaises(ImmutableRecordError):
            XPQuarantine.objects.all().delete()
        with self.assertRaises(ImmutableRecordError):
            XPQuarantine.objects.bulk_update([record], ["reason"])
        self.assertEqual(XPQuarantine.objects.get().reason, "r")
        self.assertTrue(is_quarantined(self.award))


class QuarantineAdminTests(QuarantineTestBase):
    ADD = "admin:xp_xpquarantine_add"

    def post(self, user, reason="Impossible completion time"):
        self.client.force_login(user)
        return self.client.post(reverse(self.ADD), {"entry": self.award.pk, "reason": reason})

    def test_superuser_quarantines_through_admin_with_audit(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse(self.ADD)).status_code, 200)
        self.assertEqual(self.post(self.admin).status_code, 302)
        record = XPQuarantine.objects.get()
        self.assertEqual((record.entry_id, record.flagged_by), (self.award.pk, self.admin))
        self.assertEqual(AuditLog.objects.filter(action="xp.quarantine").count(), 1)

    def test_admin_requires_a_reason(self):
        r = self.post(self.admin, reason="")
        self.assertEqual(r.status_code, 200)  # form redisplayed with an error
        self.assertFalse(XPQuarantine.objects.exists())

    def test_admin_refuses_non_awards_and_duplicates(self):
        adjustment = adjust_xp(self.student, amount=5, reason="r", actor=self.admin, idempotency_key="a1")
        self.client.force_login(self.admin)
        r = self.client.post(reverse(self.ADD), {"entry": adjustment.pk, "reason": "r"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(XPQuarantine.objects.exists())
        self.post(self.admin)
        self.assertEqual(self.post(self.admin).status_code, 200)  # already quarantined
        self.assertEqual(XPQuarantine.objects.count(), 1)

    def test_staff_without_the_permission_cannot_quarantine(self):
        for user in (make_staff("plain"), make_staff("viewer", "view_xpquarantine")):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse(self.ADD)).status_code, 403)
                self.assertEqual(self.post(user).status_code, 403)
        self.assertFalse(XPQuarantine.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action="xp.quarantine").exists())

    def test_staff_with_the_permission_can_quarantine(self):
        mod = make_staff("mod", "quarantine_xp_award")
        self.assertEqual(self.post(mod).status_code, 302)
        self.assertEqual(XPQuarantine.objects.get().flagged_by, mod)

    def test_records_are_read_only_in_admin(self):
        record = quarantine_award(self.award, actor=self.admin, reason="r")
        self.client.force_login(self.admin)
        change = reverse("admin:xp_xpquarantine_change", args=[record.pk])
        self.assertEqual(self.client.get(change).status_code, 200)  # view only
        self.client.post(change, {"entry": self.award.pk, "reason": "tampered"})
        delete = reverse("admin:xp_xpquarantine_delete", args=[record.pk])
        self.assertEqual(self.client.post(delete, {"post": "yes"}).status_code, 403)
        self.assertEqual(XPQuarantine.objects.get().reason, "r")

    def test_students_cannot_reach_the_admin(self):
        self.client.force_login(self.student)
        r = self.client.get(reverse(self.ADD))
        self.assertEqual(r.status_code, 302)  # sent to the admin login
        self.assertFalse(XPQuarantine.objects.exists())


class NoPublicEndpointTests(TestCase):
    def test_no_url_outside_admin_mentions_quarantine(self):
        def walk(patterns, prefix=""):
            for p in patterns:
                route = prefix + str(p.pattern)
                if hasattr(p, "url_patterns"):
                    if not route.startswith("admin"):
                        yield from walk(p.url_patterns, route)
                else:
                    yield route

        routes = list(walk(get_resolver().url_patterns))
        self.assertTrue(routes)
        self.assertEqual([r for r in routes if "quarantin" in r.lower()], [])

