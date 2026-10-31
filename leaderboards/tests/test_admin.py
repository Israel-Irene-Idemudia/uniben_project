"""Contribution rule admin (Phase 4.2): drafts editable with a reason,
activation gated by permission and completeness, published sets frozen."""
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse

from common.models import AuditLog
from leaderboards.models import ContributionRuleSet
from leaderboards.services import activate_rule_set, create_draft, set_item
from xp.models import XPRule
from xp.tests.helpers import make_admin, make_student

ADD_URL = reverse("admin:leaderboards_contributionruleset_add")


def form_data(items=(), initial=0, **fields):
    data = {
        "name": "Rule", "university": "", "summary": "How it works.", "student_cap": "100",
        "reason": "set up", "transition": "",
        "items-TOTAL_FORMS": str(len(items)), "items-INITIAL_FORMS": str(initial),
        "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "1000",
    }
    for i, item in enumerate(items):
        for key, value in item.items():
            data[f"items-{i}-{key}"] = value
    data.update(fields)
    return data


class ContributionRuleAdminTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.xp_rule = XPRule.objects.create(action_code="test_a", amount=1)
        self.item = {"xp_rule": str(self.xp_rule.pk), "label": "Practice", "weight": "1.25", "per_student_cap": ""}

    def test_superuser_creates_and_activates_in_one_save(self):
        self.client.force_login(self.admin)
        r = self.client.post(ADD_URL, form_data([self.item], transition="activate", reason="launch"))
        self.assertEqual(r.status_code, 302)
        rs = ContributionRuleSet.objects.get()
        self.assertEqual(rs.state, ContributionRuleSet.STATE_ACTIVE)
        self.assertEqual(str(rs.items.get().weight), "1.25")
        actions = set(AuditLog.objects.filter(target_id=str(rs.pk)).values_list("action", flat=True))
        self.assertEqual(actions, {"contribution_rules.create", "contribution_rules.activate"})

    def test_reason_is_required(self):
        self.client.force_login(self.admin)
        r = self.client.post(ADD_URL, form_data([self.item], reason=""))
        self.assertEqual(r.status_code, 200)  # form redisplayed with an error
        self.assertFalse(ContributionRuleSet.objects.exists())

    def test_incomplete_draft_is_saved_but_stays_inactive(self):
        self.client.force_login(self.admin)
        incomplete = {**self.item, "weight": "", "label": ""}
        self.client.post(ADD_URL, form_data([incomplete], student_cap="", transition="activate"))
        rs = ContributionRuleSet.objects.get()
        self.assertEqual(rs.state, ContributionRuleSet.STATE_DRAFT)
        self.assertFalse(AuditLog.objects.filter(action="contribution_rules.activate").exists())

    def test_staff_editor_without_activate_permission_cannot_publish(self):
        editor = make_student("editor")
        editor.is_staff = True
        editor.save()
        for codename in ("add_contributionruleset", "change_contributionruleset", "view_contributionruleset",
                         "add_contributionruleitem", "change_contributionruleitem", "view_contributionruleitem"):
            editor.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(editor)
        r = self.client.post(ADD_URL, form_data([self.item], transition="activate"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ContributionRuleSet.objects.get().state, ContributionRuleSet.STATE_DRAFT)

    def test_published_rule_is_read_only_in_admin_and_cannot_be_deleted(self):
        rs = create_draft(name="Live", summary="s", student_cap=10, actor=self.admin, reason="r")
        set_item(rs, xp_rule=self.xp_rule, label="Practice", weight="1", actor=self.admin, reason="r")
        activate_rule_set(rs, actor=self.admin, reason="r")
        item = rs.items.get()
        self.client.force_login(self.admin)
        url = reverse("admin:leaderboards_contributionruleset_change", args=[rs.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        edited = {**self.item, "id": str(item.pk), "rule_set": str(rs.pk), "weight": "9"}
        self.client.post(url, form_data([edited], initial=1, name="Hacked", reason="try"))
        rs.refresh_from_db()
        self.assertEqual((rs.name, rs.state, str(rs.items.get().weight)), ("Live", "active", "1.00"))
        request = RequestFactory().get("/")
        request.user = self.admin
        self.assertFalse(admin.site._registry[ContributionRuleSet].has_delete_permission(request, rs))
