from django.test import TestCase
from django.urls import reverse

from common.models import AuditLog
from xp.models import LevelConfig, XPRule
from xp.services import get_balance

from .helpers import make_admin, make_student


class AdminTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student(points=50)
        self.client.force_login(self.admin)

    def test_adjustment_form_applies_once_and_audits(self):
        url = reverse("admin:xp_xpadjustment_add")
        self.assertEqual(self.client.get(url).status_code, 200)
        audits_before = AuditLog.objects.filter(action="xp.adjustment").count()  # setUp wrote one
        data = {"user": self.student.pk, "amount": 25, "reason": "Quiz winner", "token": "tok123"}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.client.post(url, data)  # double click with the same token
        self.assertEqual(get_balance(self.student), 75)
        self.assertEqual(AuditLog.objects.filter(action="xp.adjustment").count(), audits_before + 1)

    def test_adjustment_without_reason_or_below_zero_is_refused(self):
        url = reverse("admin:xp_xpadjustment_add")
        self.client.post(url, {"user": self.student.pk, "amount": 5, "reason": "", "token": "t1"})
        self.client.post(url, {"user": self.student.pk, "amount": -500, "reason": "x", "token": "t2"})
        self.assertEqual(get_balance(self.student), 50)

    def test_rule_edit_needs_a_reason_and_is_audited(self):
        rule = XPRule.objects.get(action_code="material_verified")
        url = reverse("admin:xp_xprule_change", args=[rule.pk])
        base = {"action_code": rule.action_code, "amount": 12, "daily_cap": 50, "diminishing_percent": 50,
                "is_active": "on", "description": rule.description}
        self.client.post(url, {**base, "reason": ""})
        rule.refresh_from_db()
        self.assertEqual(rule.amount, 10)
        self.client.post(url, {**base, "reason": "Raise reward"})
        rule.refresh_from_db()
        self.assertEqual(rule.amount, 12)
        log = AuditLog.objects.get(action="xp_rule.update")
        self.assertEqual((log.before["amount"], log.after["amount"], log.reason), (10, 12, "Raise reward"))

    def test_seed_data_is_present(self):
        self.assertTrue(XPRule.objects.filter(action_code="material_verified", amount=10).exists())
        self.assertEqual(LevelConfig.objects.count(), 10)
