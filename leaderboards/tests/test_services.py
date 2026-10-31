"""Contribution rule services (Phase 4.2, BE-05.2): validation, lifecycle,
permissions, audit, multi-university resolution, contribution maths."""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import TestCase

from common.models import AuditLog, ImmutableRecordError
from core.models import University
from leaderboards.models import ContributionRuleItem, ContributionRuleSet
from leaderboards.services import (
    RuleSetError,
    activate_rule_set,
    compute_contribution,
    copy_to_draft,
    create_draft,
    get_active_rule_set,
    readiness_problems,
    retire_rule_set,
    set_item,
)
from xp.models import XPRule
from xp.tests.helpers import make_admin, make_student

D = Decimal


class RuleSetTestBase(TestCase):
    def setUp(self):
        self.admin = make_admin()
        # Test-only XP rules: no real policy values are assumed.
        self.rule_a = XPRule.objects.create(action_code="test_a", amount=1)
        self.rule_b = XPRule.objects.create(action_code="test_b", amount=1)
        self.uni = University.objects.create(name="Test Uni", code="testuni")

    def complete_draft(self, university=None, cap=100, uncapped=False, name="Rule"):
        rs = create_draft(
            name=name, university=university, summary="How it works.", student_cap=cap,
            uncapped=uncapped, actor=self.admin, reason="draft",
        )
        set_item(rs, xp_rule=self.rule_a, label="Activity A", weight="1.00", actor=self.admin, reason="r")
        return rs

    def active(self, **kw):
        return activate_rule_set(self.complete_draft(**kw), actor=self.admin, reason="publish")


class ValidationTests(RuleSetTestBase):
    def test_new_rule_sets_are_inactive_drafts(self):
        rs = create_draft(name="Rule", actor=self.admin, reason="r")
        self.assertEqual(rs.state, ContributionRuleSet.STATE_DRAFT)
        self.assertIsNone(get_active_rule_set())

    def test_incomplete_draft_lists_every_problem_and_stays_draft(self):
        rs = create_draft(name="Rule", actor=self.admin, reason="r")
        set_item(rs, xp_rule=self.rule_a, actor=self.admin, reason="r")  # no weight, no label
        problems = readiness_problems(rs)
        for expected in ("summary", "cap", "test_a: a weight", "test_a: a student-facing label"):
            self.assertTrue(any(expected in p for p in problems), expected)
        with self.assertRaises(RuleSetError):
            activate_rule_set(rs, actor=self.admin, reason="go")
        rs.refresh_from_db()
        self.assertEqual(rs.state, ContributionRuleSet.STATE_DRAFT)

    def test_no_activities_or_switched_off_rule_blocks_activation(self):
        rs = create_draft(name="R", summary="s", student_cap=5, actor=self.admin, reason="r")
        self.assertIn("Add at least one contributing activity.", readiness_problems(rs))
        set_item(rs, xp_rule=self.rule_a, label="A", weight=1, actor=self.admin, reason="r")
        self.rule_a.is_active = False
        self.rule_a.save()
        self.assertTrue(any("switched off" in p for p in readiness_problems(rs)))

    def test_inactive_university_blocks_activation(self):
        rs = self.complete_draft(university=self.uni)
        self.uni.is_active = False
        self.uni.save()
        self.assertIn("The university is not active.", readiness_problems(rs))

    def test_empty_cap_is_not_read_as_uncapped(self):
        rs = self.complete_draft(cap=None)
        self.assertTrue(any("cap" in p for p in readiness_problems(rs)))
        uncapped = self.complete_draft(cap=None, uncapped=True, name="Open")
        self.assertEqual(readiness_problems(uncapped), [])

    def test_cap_and_uncapped_together_are_refused(self):
        with self.assertRaises(RuleSetError):
            create_draft(name="R", student_cap=10, uncapped=True, actor=self.admin, reason="r")
        rs = create_draft(name="R", actor=self.admin, reason="r")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ContributionRuleSet.objects.filter(pk=rs.pk).update(student_cap=10, uncapped=True)

    def test_weight_and_caps_must_be_positive(self):
        rs = create_draft(name="R", actor=self.admin, reason="r")
        for bad in ("0", "-1", "1000"):
            with self.subTest(weight=bad), self.assertRaises(RuleSetError):
                set_item(rs, xp_rule=self.rule_a, label="A", weight=bad, actor=self.admin, reason="r")
        with self.assertRaises(RuleSetError):
            set_item(rs, xp_rule=self.rule_a, label="A", weight="1", per_student_cap=0, actor=self.admin, reason="r")
        with self.assertRaises(RuleSetError):
            create_draft(name="R", student_cap=0, actor=self.admin, reason="r")

    def test_set_item_replaces_rather_than_duplicates(self):
        rs = self.complete_draft()
        set_item(rs, xp_rule=self.rule_a, label="Renamed", weight="2.50", actor=self.admin, reason="r")
        self.assertEqual(rs.items.count(), 1)
        self.assertEqual(rs.items.get().weight, D("2.50"))

    def test_reason_is_mandatory(self):
        with self.assertRaises(RuleSetError):
            create_draft(name="R", actor=self.admin, reason="  ")
        rs = self.complete_draft()
        with self.assertRaises(RuleSetError):
            activate_rule_set(rs, actor=self.admin, reason="")


class LifecycleTests(RuleSetTestBase):
    def test_activate_is_audited_and_published(self):
        rs = self.active()
        self.assertEqual(rs.state, ContributionRuleSet.STATE_ACTIVE)
        self.assertEqual(rs.activated_by, self.admin)
        self.assertEqual(get_active_rule_set(), rs)
        log = AuditLog.objects.get(action="contribution_rules.activate")
        self.assertEqual((log.target_id, log.reason), (str(rs.pk), "publish"))
        self.assertEqual(log.after["items"][0]["weight"], "1.00")

    def test_draft_edits_are_audited(self):
        rs = self.complete_draft()
        actions = list(AuditLog.objects.filter(target_id=str(rs.pk)).values_list("action", flat=True))
        self.assertEqual(actions.count("contribution_rules.create"), 1)
        self.assertEqual(actions.count("contribution_rules.update"), 1)

    def test_activating_replaces_previous_in_same_scope_only(self):
        global_old = self.active(name="Global 1")
        uni_rule = self.active(university=self.uni, name="Uni 1")
        global_new = self.active(name="Global 2")
        for obj in (global_old, uni_rule, global_new):
            obj.refresh_from_db()
        self.assertEqual(global_old.state, ContributionRuleSet.STATE_RETIRED)
        self.assertIsNotNone(global_old.retired_at)
        self.assertEqual(uni_rule.state, ContributionRuleSet.STATE_ACTIVE)
        self.assertEqual(global_new.state, ContributionRuleSet.STATE_ACTIVE)

    def test_database_refuses_two_active_in_one_scope(self):
        a, b = self.complete_draft(), self.complete_draft(name="B")
        ContributionRuleSet.objects.filter(pk=a.pk).update(state="active")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ContributionRuleSet.objects.filter(pk=b.pk).update(state="active")

    def test_published_rule_sets_are_frozen(self):
        rs = self.active()
        rs.name = "Changed"
        with self.assertRaises(ImmutableRecordError):
            rs.save()
        with self.assertRaises(RuleSetError):
            set_item(rs, xp_rule=self.rule_b, label="B", weight=1, actor=self.admin, reason="r")
        item = rs.items.get()
        item.weight = D("9")
        with self.assertRaises(ImmutableRecordError):
            item.save()
        with self.assertRaises(ImmutableRecordError):
            item.delete()
        with self.assertRaises(ImmutableRecordError):
            ContributionRuleItem.objects.create(rule_set=rs, xp_rule=self.rule_b, label="B", weight=1)

    def test_retire_is_final_and_cannot_retire_a_draft(self):
        with self.assertRaises(RuleSetError):
            retire_rule_set(self.complete_draft(), actor=self.admin, reason="r")
        rs = self.active()
        retire_rule_set(rs, actor=self.admin, reason="withdrawn")
        self.assertIsNone(get_active_rule_set())
        with self.assertRaises(RuleSetError):
            activate_rule_set(rs, actor=self.admin, reason="again")
        self.assertTrue(AuditLog.objects.filter(action="contribution_rules.retire", reason="withdrawn").exists())

    def test_copy_to_draft_keeps_the_original_untouched(self):
        rs = self.active()
        copy = copy_to_draft(rs, actor=self.admin, reason="tune weights")
        self.assertEqual(copy.state, ContributionRuleSet.STATE_DRAFT)
        self.assertEqual(copy.items.get().weight, D("1.00"))
        set_item(copy, xp_rule=self.rule_a, label="Activity A", weight="2", actor=self.admin, reason="r")
        self.assertEqual(rs.items.get().weight, D("1.00"))
        activate_rule_set(copy, actor=self.admin, reason="go")
        rs.refresh_from_db()
        self.assertEqual(rs.state, ContributionRuleSet.STATE_RETIRED)



class PermissionTests(RuleSetTestBase):
    def setUp(self):
        super().setUp()
        self.editor = make_student("editor")
        self.editor.is_staff = True
        self.editor.save()

    def test_staff_without_permission_cannot_activate_or_retire(self):
        rs = self.complete_draft()
        with self.assertRaises(RuleSetError):
            activate_rule_set(rs, actor=self.editor, reason="go")
        with self.assertRaises(RuleSetError):
            activate_rule_set(rs, actor=None, reason="go")
        rs.refresh_from_db()
        self.assertEqual(rs.state, ContributionRuleSet.STATE_DRAFT)
        live = self.active(name="Live")
        with self.assertRaises(RuleSetError):
            retire_rule_set(live, actor=self.editor, reason="r")

    def test_explicit_permission_allows_activation(self):
        self.editor.user_permissions.add(Permission.objects.get(codename="activate_contributionruleset"))
        editor = type(self.editor).objects.get(pk=self.editor.pk)  # fresh permission cache
        rs = activate_rule_set(self.complete_draft(), actor=editor, reason="go")
        self.assertEqual(rs.state, ContributionRuleSet.STATE_ACTIVE)


class ResolutionTests(RuleSetTestBase):
    def test_university_rule_overrides_global_and_others_fall_back(self):
        other = University.objects.create(name="Other", code="other")
        global_rule = self.active(name="Global")
        uni_rule = self.active(university=self.uni, name="Own")
        self.assertEqual(get_active_rule_set(self.uni), uni_rule)
        self.assertEqual(get_active_rule_set(self.uni.pk), uni_rule)
        self.assertEqual(get_active_rule_set(other), global_rule)
        self.assertEqual(get_active_rule_set(None), global_rule)

    def test_no_global_means_none_for_other_universities(self):
        self.active(university=self.uni)
        self.assertIsNone(get_active_rule_set(None))
        self.assertIsNone(get_active_rule_set(University.objects.create(name="O", code="o")))


class ContributionMathTests(RuleSetTestBase):
    def rule(self, cap=None, uncapped=False, item_cap=None):
        rs = create_draft(name="R", summary="s", student_cap=cap, uncapped=uncapped, actor=self.admin, reason="r")
        set_item(rs, xp_rule=self.rule_a, label="A", weight="1.50", per_student_cap=item_cap, actor=self.admin, reason="r")
        set_item(rs, xp_rule=self.rule_b, label="B", weight="0.50", actor=self.admin, reason="r")
        return rs

    def test_weighted_sum_ignores_unlisted_and_negative(self):
        rs = self.rule(uncapped=True)
        # 1.5 x 10 + 0.5 x 4 = 17; "other" is not in the rule.
        self.assertEqual(compute_contribution(rs, {"test_a": 10, "test_b": 4, "other": 99}), D("17"))
        self.assertEqual(compute_contribution(rs, {"test_a": -5}), D("0"))
        self.assertEqual(compute_contribution(rs, {}), D("0"))

    def test_per_activity_cap_then_student_cap(self):
        # A: min(15, 6) = 6, B: 2 -> 8
        self.assertEqual(compute_contribution(self.rule(uncapped=True, item_cap=6), {"test_a": 10, "test_b": 4}), D("8"))
        # 17, limited to the per-student cap of 12
        self.assertEqual(compute_contribution(self.rule(cap=12), {"test_a": 10, "test_b": 4}), D("12"))

    def test_incomplete_item_is_refused_not_guessed(self):
        rs = create_draft(name="R", actor=self.admin, reason="r")
        set_item(rs, xp_rule=self.rule_a, actor=self.admin, reason="r")
        with self.assertRaises(RuleSetError):
            compute_contribution(rs, {"test_a": 1})

