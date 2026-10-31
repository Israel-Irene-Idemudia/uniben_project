"""Season services (Phase 4.1, BE-20.2): lifecycle, audit, Lagos boundaries."""
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase

from common.models import AuditLog
from seasons.models import Season
from seasons.services import (
    SeasonError, close_season, create_season, current_season, open_season, reschedule_season,
)

User = get_user_model()
LAGOS = ZoneInfo("Africa/Lagos")


def lagos(y, m, d):
    return datetime(y, m, d, tzinfo=LAGOS)


class SeasonServiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "b@test.com", "x")

    def week(self, start=None, name="Week 1"):
        start = start or lagos(2026, 11, 2)
        return create_season(
            name=name, kind="week", starts_at=start, ends_at=start + timedelta(days=7),
            actor=self.admin, reason="schedule",
        )

    def test_create_is_scheduled_and_audited(self):
        s = self.week()
        self.assertEqual(s.state, Season.STATE_SCHEDULED)
        log = AuditLog.objects.get(action="season.create")
        self.assertEqual((log.target_id, log.reason), (str(s.pk), "schedule"))

    def test_lagos_midnight_is_stored_as_utc(self):
        s = self.week()
        s.refresh_from_db()
        # Lagos is UTC+1, no DST: Monday 00:00 Lagos is Sunday 23:00 UTC.
        self.assertEqual(s.starts_at.astimezone(dt_timezone.utc), datetime(2026, 11, 1, 23, tzinfo=dt_timezone.utc))

    def test_naive_datetimes_are_read_as_lagos(self):
        s = create_season(name="T", kind="term", starts_at=datetime(2027, 1, 1), ends_at=datetime(2027, 4, 1), actor=self.admin, reason="r")
        self.assertEqual(s.starts_at.astimezone(dt_timezone.utc).hour, 23)

    def test_reason_is_mandatory(self):
        with self.assertRaises(SeasonError):
            create_season(name="x", kind="week", starts_at=lagos(2026, 11, 2), ends_at=lagos(2026, 11, 9), actor=self.admin, reason="  ")

    def test_end_must_follow_start(self):
        with self.assertRaises(SeasonError):
            create_season(name="x", kind="week", starts_at=lagos(2026, 11, 9), ends_at=lagos(2026, 11, 2), actor=self.admin, reason="r")

    def test_same_kind_cannot_overlap_but_other_kind_can(self):
        self.week()
        with self.assertRaises(SeasonError):
            self.week(start=lagos(2026, 11, 5), name="Clash")
        self.week(start=lagos(2026, 11, 9), name="Week 2")  # back-to-back is fine
        create_season(name="Term", kind="term", starts_at=lagos(2026, 10, 1), ends_at=lagos(2027, 2, 1), actor=self.admin, reason="r")

    def test_full_lifecycle_is_audited(self):
        s = self.week()
        open_season(s, actor=self.admin, reason="go")
        self.assertEqual(current_season("week"), s)
        close_season(s, actor=self.admin, reason="done")
        s.refresh_from_db()
        self.assertEqual(s.state, Season.STATE_CLOSED)
        self.assertIsNotNone(s.opened_at)
        self.assertIsNotNone(s.closed_at)
        self.assertIsNone(current_season("week"))
        actions = AuditLog.objects.filter(target_type="Season").values_list("action", flat=True)
        self.assertCountEqual(actions, ["season.create", "season.open", "season.close"])

    def test_states_only_move_forward(self):
        s = self.week()
        with self.assertRaises(SeasonError):
            close_season(s, actor=self.admin, reason="r")
        open_season(s, actor=self.admin, reason="r")
        with self.assertRaises(SeasonError):
            open_season(s, actor=self.admin, reason="r")
        close_season(s, actor=self.admin, reason="r")
        with self.assertRaises(SeasonError):
            open_season(s, actor=self.admin, reason="reopen")  # closed is final

    def test_only_one_open_season_per_kind(self):
        a, b = self.week(), self.week(start=lagos(2026, 11, 9), name="Week 2")
        open_season(a, actor=self.admin, reason="r")
        with self.assertRaises(SeasonError):
            open_season(b, actor=self.admin, reason="r")

    def test_database_also_refuses_two_open_seasons(self):
        a, b = self.week(), self.week(start=lagos(2026, 11, 9), name="Week 2")
        Season.objects.filter(pk=a.pk).update(state="open")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Season.objects.filter(pk=b.pk).update(state="open")

    def test_only_scheduled_seasons_can_be_rescheduled(self):
        s = self.week()
        reschedule_season(s, name="Renamed", starts_at=lagos(2026, 11, 3), ends_at=lagos(2026, 11, 10), actor=self.admin, reason="moved")
        s.refresh_from_db()
        self.assertEqual(s.name, "Renamed")
        self.assertTrue(AuditLog.objects.filter(action="season.update").exists())
        open_season(s, actor=self.admin, reason="r")
        with self.assertRaises(SeasonError):
            reschedule_season(s, name="x", starts_at=lagos(2026, 11, 4), ends_at=lagos(2026, 11, 11), actor=self.admin, reason="r")

    def test_admin_cannot_delete_seasons(self):
        request = RequestFactory().get("/")
        request.user = self.admin
        self.assertFalse(admin.site._registry[Season].has_delete_permission(request))
