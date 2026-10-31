"""Season admin: create and open through the form, audited (Phase 4.1)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from common.models import AuditLog
from seasons.models import Season

User = get_user_model()
ADD_URL = "/admin/tps/seasons/season/add/"


class SeasonAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "b@test.com", "x")
        self.client.force_login(self.admin)

    def post_new(self, **extra):
        data = {
            "name": "Week 1", "kind": "week",
            "starts_at_0": "2026-11-02", "starts_at_1": "00:00:00",
            "ends_at_0": "2026-11-09", "ends_at_1": "00:00:00",
            "reason": "first week", "transition": "",
        }
        data.update(extra)
        return self.client.post(ADD_URL, data)

    def test_create_and_open_from_admin_is_audited(self):
        r = self.post_new(transition="open")
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["adminform"].form.errors)
        season = Season.objects.get()
        self.assertEqual(season.state, Season.STATE_OPEN)
        self.assertCountEqual(
            AuditLog.objects.filter(target_type="Season").values_list("action", flat=True),
            ["season.create", "season.open"],
        )

    def test_reason_required(self):
        r = self.post_new(reason="")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Season.objects.exists())

    def test_overlap_rejected_in_form(self):
        self.post_new()
        r = self.post_new(name="Clash", starts_at_0="2026-11-05", ends_at_0="2026-11-12")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Season.objects.count(), 1)

    def test_close_from_change_form(self):
        self.post_new(transition="open")
        season = Season.objects.get()
        url = f"/admin/tps/seasons/season/{season.pk}/change/"
        r = self.client.post(url, {"reason": "week over", "transition": "close"})
        self.assertEqual(r.status_code, 302)
        season.refresh_from_db()
        self.assertEqual(season.state, Season.STATE_CLOSED)
