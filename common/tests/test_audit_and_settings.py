from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from common.models import AuditLog, FeatureFlag, ImmutableRecordError, PlatformSetting
from common.request_context import reset_request_id, set_request_id
from common.services import get_setting, log_audit, set_setting


def make_user(name):
    # No password on purpose: hashing is slow and these tests never log in with one.
    return get_user_model().objects.create_user(name)


class AuditLogImmutabilityTests(TestCase):
    def setUp(self):
        self.user = make_user("auditor")
        self.entry = log_audit(
            actor=self.user,
            action="test.action",
            target_type="Thing",
            target_id=1,
            reason="why",
        )

    def fresh(self):
        return AuditLog.objects.get(pk=self.entry.pk)

    def test_row_records_actor_and_a_readable_label(self):
        self.assertEqual(self.entry.actor, self.user)
        self.assertEqual(self.entry.actor_label, "auditor")
        self.assertEqual(self.entry.target_id, "1")

    def test_existing_row_cannot_be_saved_again(self):
        row = self.fresh()
        row.reason = "tampered"
        with self.assertRaises(ImmutableRecordError):
            row.save()
        self.assertEqual(self.fresh().reason, "why")

    def test_row_cannot_be_deleted(self):
        with self.assertRaises(ImmutableRecordError):
            self.fresh().delete()
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_queryset_update_is_blocked(self):
        with self.assertRaises(ImmutableRecordError):
            AuditLog.objects.all().update(reason="tampered")
        self.assertEqual(self.fresh().reason, "why")

    def test_queryset_delete_is_blocked(self):
        with self.assertRaises(ImmutableRecordError):
            AuditLog.objects.all().delete()
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_bulk_update_is_blocked(self):
        with self.assertRaises(ImmutableRecordError):
            AuditLog.objects.bulk_update([self.fresh()], ["reason"])

    def test_actor_with_audit_history_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.user.delete()


class SettingsServiceTests(TestCase):
    def setUp(self):
        self.user = make_user("svc")

    def test_set_setting_creates_the_row_and_audits_it(self):
        setting = set_setting(
            "xp.daily_cap",
            {"limit": 5},
            actor=self.user,
            reason="Initial value",
            description="Daily cap",
        )
        self.assertEqual(setting.value, {"limit": 5})
        entry = AuditLog.objects.get()
        self.assertEqual(
            (entry.action, entry.target_type, entry.target_id),
            ("setting.create", "PlatformSetting", "xp.daily_cap"),
        )
        self.assertIsNone(entry.before)
        self.assertEqual(entry.after["value"], {"limit": 5})
        self.assertEqual(entry.reason, "Initial value")
        self.assertEqual(entry.actor, self.user)
        self.assertEqual(entry.actor_label, "svc")

    def test_changing_a_value_audits_before_and_after(self):
        set_setting("xp.daily_cap", 5, actor=self.user, reason="Initial")
        set_setting("xp.daily_cap", 8, actor=self.user, reason="Raise cap")
        self.assertEqual(AuditLog.objects.count(), 2)
        entry = AuditLog.objects.filter(action="setting.update").get()
        self.assertEqual(entry.before["value"], 5)
        self.assertEqual(entry.after["value"], 8)
        self.assertEqual(entry.reason, "Raise cap")
        self.assertEqual(PlatformSetting.objects.get(key="xp.daily_cap").value, 8)

    def test_setting_the_same_value_writes_no_audit_row(self):
        set_setting("xp.daily_cap", 5, actor=self.user, reason="Initial")
        set_setting("xp.daily_cap", 5, actor=self.user, reason="No change")
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_a_reason_is_required(self):
        with self.assertRaises(ValueError):
            set_setting("xp.daily_cap", 5, actor=self.user, reason="   ")
        self.assertEqual(PlatformSetting.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_invalid_keys_are_rejected(self):
        for bad in ("Bad Key!", "", "UPPER", "x" * 101):
            with self.subTest(key=bad):
                with self.assertRaises(ValueError):
                    set_setting(bad, 1, actor=self.user, reason="test")
        self.assertEqual(PlatformSetting.objects.count(), 0)

    def test_get_setting_returns_the_default_when_missing(self):
        self.assertEqual(get_setting("missing.key", default="fallback"), "fallback")

    def test_get_setting_returns_falsy_stored_values_not_the_default(self):
        set_setting("flag.zero", 0, actor=self.user, reason="test")
        self.assertEqual(get_setting("flag.zero", default=99), 0)

    def test_audit_row_picks_up_the_current_request_id(self):
        token = set_request_id("req-9")
        try:
            set_setting("xp.daily_cap", 5, actor=self.user, reason="test")
        finally:
            reset_request_id(token)
        self.assertEqual(AuditLog.objects.get().request_id, "req-9")


class AdminAuditTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("auditadmin")
        self.client.force_login(self.admin)

    def test_adding_a_setting_in_admin_is_audited(self):
        response = self.client.post(
            reverse("admin:common_platformsetting_add"),
            {
                "key": "xp.daily_cap",
                "value": '{"limit": 5}',
                "description": "Daily cap",
                "reason": "Initial value",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PlatformSetting.objects.get(key="xp.daily_cap").value, {"limit": 5})
        entry = AuditLog.objects.get(action="setting.create")
        self.assertEqual(entry.reason, "Initial value")
        self.assertEqual(entry.actor, self.admin)
        self.assertTrue(entry.request_id)

    def test_changing_a_setting_in_admin_is_audited(self):
        setting = set_setting("xp.daily_cap", {"limit": 5}, actor=self.admin, reason="Initial")
        response = self.client.post(
            reverse("admin:common_platformsetting_change", args=[setting.pk]),
            {"value": '{"limit": 10}', "description": "Daily cap", "reason": "Raise cap"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_setting("xp.daily_cap"), {"limit": 10})
        entry = AuditLog.objects.get(action="setting.update")
        self.assertEqual(entry.before["value"], {"limit": 5})
        self.assertEqual(entry.after["value"], {"limit": 10})
        self.assertEqual(entry.reason, "Raise cap")

    def test_a_setting_change_without_a_reason_is_rejected(self):
        response = self.client.post(
            reverse("admin:common_platformsetting_add"),
            {"key": "xp.daily_cap", "value": "5", "description": ""},
        )
        self.assertEqual(response.status_code, 200)  # form re-shown with errors
        self.assertEqual(PlatformSetting.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_a_flag_change_in_admin_is_audited(self):
        flag = FeatureFlag.objects.create(name="admin_flag", enabled=False)
        response = self.client.post(
            reverse("admin:common_featureflag_change", args=[flag.pk]),
            {
                "name": "admin_flag",
                "description": "",
                "enabled": "on",
                "audience": "all",
                "reason": "Pilot with testers",
            },
        )
        self.assertEqual(response.status_code, 302)
        flag.refresh_from_db()
        self.assertTrue(flag.enabled)
        entry = AuditLog.objects.get(target_type="FeatureFlag", target_id="admin_flag")
        self.assertEqual(entry.action, "flag.update")
        self.assertFalse(entry.before["enabled"])
        self.assertTrue(entry.after["enabled"])
        self.assertEqual(entry.reason, "Pilot with testers")
        self.assertEqual(entry.actor, self.admin)

    def test_a_flag_change_without_a_reason_is_rejected(self):
        flag = FeatureFlag.objects.create(name="admin_flag", enabled=False)
        response = self.client.post(
            reverse("admin:common_featureflag_change", args=[flag.pk]),
            {"name": "admin_flag", "description": "", "enabled": "on", "audience": "all"},
        )
        self.assertEqual(response.status_code, 200)
        flag.refresh_from_db()
        self.assertFalse(flag.enabled)
        self.assertFalse(AuditLog.objects.filter(target_type="FeatureFlag").exists())

    def test_audit_log_admin_is_read_only(self):
        entry = log_audit(actor=self.admin, action="t.a", target_type="T", target_id=1)
        self.assertEqual(self.client.get(reverse("admin:common_auditlog_add")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("admin:common_auditlog_delete", args=[entry.pk])).status_code,
            403,
        )

    def test_flags_cannot_be_deleted_in_admin(self):
        flag = FeatureFlag.objects.create(name="admin_flag")
        response = self.client.get(reverse("admin:common_featureflag_delete", args=[flag.pk]))
        self.assertEqual(response.status_code, 403)