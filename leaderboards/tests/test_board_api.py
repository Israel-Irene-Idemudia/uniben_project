"""GET /api/v1/leaderboards/{scope}/{period} (Phase 4.3, BE-05.1, BE-05.3):
auth, permissions, university isolation, defaults, parameters, shape."""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AccountStatus, UserProfile
from seasons.models import Season

from .board_helpers import earn, lagos, make_world, season, spend, student

BASE = "/api/v1/leaderboards"


class PersonalLeaderboardApiTests(TestCase):
    def setUp(self):
        self.w = make_world()
        self.me = student("me", self.w["physics"], first_name="Ada", last_name="Obi")
        self.rival = student("rival", self.w["chemistry"])
        self.foreign = student("foreign", self.w["civil"])
        earn(self.me, 30, when=lagos(2026, 11, 3))
        earn(self.rival, 50, when=lagos(2026, 11, 3))
        earn(self.foreign, 99, when=lagos(2026, 11, 3))
        self.client = APIClient()
        self.client.force_authenticate(self.me)

    def get(self, path, **params):
        return self.client.get(f"{BASE}/{path}", params)

    def test_requires_authentication(self):
        r = APIClient().get(f"{BASE}/university/lifetime")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "not_authenticated")

    def test_suspended_students_cannot_read_boards(self):
        AccountStatus.objects.create(user=self.me, state=AccountStatus.SUSPENDED)
        r = self.get("university/lifetime")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["code"], "permission_denied")

    def test_unknown_scope_or_period_is_404(self):
        self.assertEqual(self.get("planet/lifetime").json()["code"], "not_found")
        self.assertEqual(self.get("university/month").status_code, 404)

    def test_university_board_is_the_callers_own_only(self):
        body = self.get("university/lifetime").json()
        self.assertEqual(body["university"], {"id": self.w["u1"].id, "name": "Uni One", "code": "uni1"})
        self.assertEqual(body["unit"]["id"], self.w["u1"].id)
        self.assertEqual([e["user"]["id"] for e in body["entries"]], [self.rival.id, self.me.id])
        self.assertEqual(body["total"], 2)

    def test_shape_and_no_private_data(self):
        body = self.client.get(f"{BASE}/university/lifetime/").json()
        self.assertEqual(
            set(body),
            {"scope", "period", "university", "unit", "season", "total", "offset", "limit",
             "next_offset", "me", "top", "entries", "around_me"},
        )
        self.assertEqual(
            body["me"],
            {"rank": 2, "position": 2, "xp": 30, "is_me": True,
             "user": {"id": self.me.id, "username": "me", "display_name": "Ada Obi"}},
        )
        self.assertEqual(set(body["entries"][0]["user"]), {"id", "username", "display_name"})
        self.assertIsNone(body["season"])

    def test_department_and_faculty_default_to_the_callers_own(self):
        dept = self.get("department/lifetime").json()
        self.assertEqual(dept["unit"]["id"], self.w["physics"].id)
        self.assertEqual([e["user"]["id"] for e in dept["entries"]], [self.me.id])
        fac = self.get("faculty/lifetime").json()
        self.assertEqual(fac["unit"]["id"], self.w["science"].id)
        self.assertEqual(fac["total"], 2)

    def test_another_unit_in_the_same_university_can_be_viewed(self):
        body = self.get("department/lifetime", department_id=self.w["chemistry"].id).json()
        self.assertEqual(body["unit"]["name"], "Chemistry")
        self.assertIsNone(body["me"])
        self.assertEqual(body["around_me"], [])

    def test_another_universitys_units_are_404(self):
        r = self.get("department/lifetime", department_id=self.w["civil"].id)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.get("faculty/lifetime", faculty_id=self.w["eng"].id).status_code, 404)
        self.assertEqual(self.get("faculty/lifetime", faculty_id=999999).status_code, 404)

    def test_spending_does_not_change_the_api_rank(self):
        spend(self.rival, 45, when=lagos(2026, 11, 4))
        body = self.get("university/lifetime").json()
        self.assertEqual(
            [(e["user"]["id"], e["xp"]) for e in body["entries"]], [(self.rival.id, 50), (self.me.id, 30)]
        )

    def test_no_open_week_is_an_empty_board(self):
        body = self.get("university/week").json()
        self.assertEqual((body["season"], body["total"], body["entries"], body["me"]), (None, 0, [], None))

    def test_open_week_and_closed_season_by_id(self):
        week = season(Season.KIND_WEEK, lagos(2026, 11, 2), lagos(2026, 11, 9))
        body = self.get("university/week").json()
        self.assertEqual(body["season"]["id"], week.id)
        self.assertEqual(body["total"], 2)
        old = season(Season.KIND_WEEK, lagos(2026, 10, 26), lagos(2026, 11, 2), state=Season.STATE_CLOSED)
        body = self.get("university/week", season_id=old.id).json()
        self.assertEqual((body["season"]["id"], body["total"]), (old.id, 0))

    def test_season_id_rules(self):
        week = season(Season.KIND_WEEK, lagos(2026, 11, 2), lagos(2026, 11, 9))
        later = season(Season.KIND_WEEK, lagos(2026, 11, 9), lagos(2026, 11, 16), state=Season.STATE_SCHEDULED)
        self.assertEqual(self.get("university/season", season_id=week.id).status_code, 404)  # wrong kind
        self.assertEqual(self.get("university/week", season_id=later.id).status_code, 404)  # not shown yet
        r = self.get("university/lifetime", season_id=week.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn("season_id", r.json()["field_errors"])

    def test_bad_paging_parameters_are_field_errors(self):
        cases = ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"around": "x"}, {"department_id": "x"})
        for params in cases:
            with self.subTest(params=params):
                r = self.get("department/lifetime", **params)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(set(r.json()["field_errors"]), set(params))

    def test_next_offset(self):
        body = self.get("university/lifetime", limit=1).json()
        self.assertEqual((len(body["entries"]), body["next_offset"]), (1, 1))
        self.assertIsNone(self.get("university/lifetime", limit=1, offset=1).json()["next_offset"])

    def test_student_without_profile_gets_empty_boards_and_no_profile_is_created(self):
        loner = student("loner")
        UserProfile.objects.filter(user=loner).delete()
        client = APIClient()
        client.force_authenticate(loner)
        for scope in ("department", "faculty", "university"):
            body = client.get(f"{BASE}/{scope}/lifetime").json()
            self.assertEqual((body["unit"], body["entries"]), (None, []))
        r = client.get(f"{BASE}/faculty/lifetime", {"faculty_id": self.w["science"].id})
        self.assertEqual(r.status_code, 404)
        self.assertFalse(UserProfile.objects.filter(user=loner).exists())

    def test_read_only(self):
        self.assertEqual(self.client.post(f"{BASE}/university/lifetime", {}, format="json").status_code, 405)

