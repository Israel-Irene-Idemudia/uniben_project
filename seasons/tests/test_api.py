"""GET /api/v1/seasons/current (Phase 4.1)."""
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AccountStatus
from seasons.services import create_season, open_season

User = get_user_model()
LAGOS = ZoneInfo("Africa/Lagos")


def lagos(y, m, d):
    return datetime(y, m, d, tzinfo=LAGOS)


class CurrentSeasonApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "b@test.com", "x")
        self.student = User.objects.create_user("stu", "s@test.com", "Pass#12345")
        self.client = APIClient()

    def season(self, name, kind, start, end):
        return create_season(name=name, kind=kind, starts_at=start, ends_at=end, actor=self.admin, reason="r")

    def test_requires_authentication(self):
        r = self.client.get("/api/v1/seasons/current")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "not_authenticated")

    def test_nulls_when_nothing_is_open(self):
        self.client.force_authenticate(self.student)
        r = self.client.get("/api/v1/seasons/current")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"week": None, "term": None})

    def test_returns_open_week_and_term_only(self):
        week = self.season("Week 1", "week", lagos(2026, 11, 2), lagos(2026, 11, 9))
        self.season("Later", "week", lagos(2026, 11, 9), lagos(2026, 11, 16))  # scheduled, hidden
        term = self.season("Harmattan", "term", lagos(2026, 10, 1), lagos(2027, 2, 1))
        open_season(week, actor=self.admin, reason="r")
        open_season(term, actor=self.admin, reason="r")
        self.client.force_authenticate(self.student)
        body = self.client.get("/api/v1/seasons/current/").json()
        self.assertEqual(body["week"]["id"], week.id)
        self.assertEqual(body["week"]["state"], "open")
        self.assertEqual(body["term"]["name"], "Harmattan")
        self.assertEqual(set(body["week"]), {"id", "name", "kind", "state", "starts_at", "ends_at"})

    def test_read_only(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.post("/api/v1/seasons/current", {}, format="json").status_code, 405)

    def test_suspended_students_can_still_read_dates(self):
        AccountStatus.objects.create(user=self.student, state=AccountStatus.SUSPENDED)
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get("/api/v1/seasons/current").status_code, 200)
