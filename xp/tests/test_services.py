from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase

from accounts.models import UserProfile
from common.models import AuditLog
from xp.models import XPLedgerEntry, XPRule
from xp.services import (
    AdjustmentRefused,
    IdempotencyConflict,
    InsufficientPoints,
    UnknownXPAction,
    adjust_xp,
    award_xp,
    get_balance,
    get_level,
    get_lifetime_xp,
    get_summary,
    lagos_day_bounds,
    spend_points,
)

from .helpers import give_points, make_admin, make_student

LAGOS = ZoneInfo("Africa/Lagos")


def set_rule(code="test_action", amount=10, cap=None, after=None, percent=50, active=True):
    XPRule.objects.update_or_create(
        action_code=code,
        defaults=dict(amount=amount, daily_cap=cap, diminishing_after=after,
                      diminishing_percent=percent, is_active=active),
    )


class AwardTests(TestCase):
    def setUp(self):
        self.user = make_student()
        set_rule()

    def award(self, record="1", **kw):
        return award_xp(self.user, action_code="test_action", source_feature="t", source_record_id=record, **kw)

    def test_replaying_the_same_event_awards_once(self):
        first = self.award("42")
        second = self.award("42")
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.entry.pk, second.entry.pk)
        self.assertEqual(get_balance(self.user), 10)
        self.assertEqual(XPLedgerEntry.objects.filter(user=self.user).count(), 1)

    def test_same_key_for_a_different_event_is_a_conflict(self):
        self.award("1", idempotency_key="shared-key")
        with self.assertRaises(IdempotencyConflict):
            self.award("2", idempotency_key="shared-key")

    def test_unknown_or_switched_off_action_is_refused(self):
        with self.assertRaises(UnknownXPAction):
            award_xp(self.user, action_code="nope", source_feature="t", source_record_id="1")
        set_rule(active=False)
        with self.assertRaises(UnknownXPAction):
            self.award("1")

    def test_bad_inputs_are_rejected(self):
        for bad in (0, -5, 1.5, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.award("x", amount=bad)
        with self.assertRaises(ValueError):
            award_xp(self.user, action_code="test_action", source_feature="t")  # no key, no record

    def test_server_side_amount_override_is_used(self):
        self.assertEqual(self.award("1", amount=25).entry.amount, 25)

    def test_daily_cap_pays_partial_then_zero_and_replay_cannot_pay(self):
        set_rule(cap=25)
        self.assertEqual(self.award("1").entry.amount, 10)
        self.assertEqual(self.award("2").entry.amount, 10)
        partial = self.award("3")
        self.assertEqual(partial.entry.amount, 5)
        self.assertEqual(partial.entry.metadata["capped"], "partial")
        capped = self.award("4")
        self.assertTrue(capped.capped)
        self.assertEqual(capped.entry.amount, 0)
        self.assertEqual(get_balance(self.user), 25)
        # Replaying the capped event later must not pay out.
        next_day = datetime(2099, 1, 2, 12, 0, tzinfo=LAGOS)
        with mock.patch("django.utils.timezone.now", return_value=next_day):
            again = self.award("4")
        self.assertFalse(again.created)
        self.assertEqual(get_balance(self.user), 25)

    def test_diminishing_returns(self):
        set_rule(after=2, percent=50)
        amounts = [self.award(str(i)).entry.amount for i in range(4)]
        self.assertEqual(amounts, [10, 10, 5, 5])

    def test_cap_resets_at_the_lagos_midnight_not_utc(self):
        set_rule(cap=10)
        late = datetime(2026, 10, 30, 23, 30, tzinfo=LAGOS)      # 22:30 UTC
        just_after = datetime(2026, 10, 31, 0, 30, tzinfo=LAGOS)  # 23:30 UTC, same UTC day
        with mock.patch("django.utils.timezone.now", return_value=late):
            self.assertEqual(self.award("1").entry.amount, 10)
            self.assertTrue(self.award("2").capped)
        with mock.patch("django.utils.timezone.now", return_value=just_after):
            self.assertEqual(self.award("3").entry.amount, 10)

    def test_lagos_day_bounds(self):
        start, end = lagos_day_bounds(datetime(2026, 10, 30, 23, 30, tzinfo=LAGOS))
        self.assertEqual(start, datetime(2026, 10, 30, 0, 0, tzinfo=LAGOS))
        self.assertEqual(end, datetime(2026, 10, 31, 0, 0, tzinfo=LAGOS))


class SpendAndBalanceTests(TestCase):
    def setUp(self):
        self.user = make_student(points=100)

    def spend(self, cost=60, key="s1", record="r1"):
        return spend_points(self.user, cost=cost, reason_code="reward_redeem", source_feature="rewards",
                            source_record_id=record, idempotency_key=key)

    def test_spend_lowers_balance_but_not_lifetime_xp_or_level(self):
        level_before = get_level(self.user)
        self.spend(60)
        self.assertEqual(get_balance(self.user), 40)
        self.assertEqual(get_lifetime_xp(self.user), 100)  # D-2
        self.assertEqual(get_level(self.user).level, level_before.level)

    def test_cannot_overspend(self):
        with self.assertRaises(InsufficientPoints) as ctx:
            self.spend(150)
        self.assertEqual((ctx.exception.balance, ctx.exception.cost), (100, 150))
        self.assertEqual(get_balance(self.user), 100)

    def test_zero_negative_and_non_integer_costs_are_rejected(self):
        for bad in (0, -50, 1.9, True, "50"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.spend(bad)
        self.assertEqual(get_balance(self.user), 100)

    def test_replaying_a_spend_charges_once(self):
        a, b = self.spend(), self.spend()
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(get_balance(self.user), 40)

    def test_same_key_different_spend_conflicts(self):
        self.spend(60, key="k")
        with self.assertRaises(IdempotencyConflict):
            self.spend(30, key="k")

    def test_ledger_balance_always_matches_the_profile_mirror(self):
        award_xp  # imported for clarity of intent
        self.spend(60)
        self.assertEqual(UserProfile.objects.get(user=self.user).points, get_balance(self.user))


class AdjustmentTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.user = make_student(points=50)

    def test_adjustment_writes_ledger_and_audit_once(self):
        entry = adjust_xp(self.user, amount=20, reason="Prize", actor=self.admin, idempotency_key="adj1")
        again = adjust_xp(self.user, amount=20, reason="Prize", actor=self.admin, idempotency_key="adj1")
        self.assertEqual(entry.pk, again.pk)
        self.assertEqual(get_balance(self.user), 70)
        logs = AuditLog.objects.filter(action="xp.adjustment", target_id=str(entry.pk))
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.get().reason, "Prize")

    def test_reason_and_actor_are_mandatory(self):
        with self.assertRaises(ValueError):
            adjust_xp(self.user, amount=5, reason="  ", actor=self.admin, idempotency_key="k")
        with self.assertRaises(ValueError):
            adjust_xp(self.user, amount=5, reason="x", actor=None, idempotency_key="k")

    def test_cannot_deduct_below_zero(self):
        with self.assertRaises(AdjustmentRefused):
            adjust_xp(self.user, amount=-51, reason="x", actor=self.admin, idempotency_key="k")
        with self.assertRaises(AdjustmentRefused):
            adjust_xp(self.user, amount=0, reason="x", actor=self.admin, idempotency_key="k0")
        self.assertEqual(get_balance(self.user), 50)


class LevelTests(TestCase):
    """Uses the curve seeded by migration 0002 (D-12)."""

    def test_levels_follow_lifetime_xp(self):
        user = make_student()
        self.assertEqual((get_level(user).level, get_level(user).xp_to_next_level), (1, 100))
        give_points(user, 100)
        info = get_level(user)
        self.assertEqual((info.level, info.title, info.xp_to_next_level), (2, "Learner", 150))
        give_points(user, 5000)
        top = get_level(user)
        self.assertEqual(top.level, 10)
        self.assertIsNone(top.xp_to_next_level)

    def test_summary_shape(self):
        user = make_student(points=100)
        summary = get_summary(user)
        self.assertEqual(set(summary), {"lifetime_xp", "balance", "level", "level_title", "xp_to_next_level"})
