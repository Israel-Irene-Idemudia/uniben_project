"""GET /api/v1/leaderboards/{scope}/{period} — Phase 4.4 board endpoint
(BE-05.3): rank, neighbours and top entries in ONE response from ONE board
query, whatever page the caller is on."""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .board_helpers import earn, lagos, make_world, student

BASE = "/api/v1/leaderboards"


def positions(entries):
    return [e["position"] for e in entries]


class BoardEndpointOneResponseTests(TestCase):
    """SRS BE-05 acceptance: a student ranked 47th sees themselves, their
    neighbours and the top 10 in a single API response."""

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.users = []
        # 60 students, distinct scores: position n has 1000 - n XP.
        for n in range(1, 61):
            user = student(f"s{n:02d}", cls.w["physics"])
            earn(user, 1000 - n, when=lagos(2026, 11, 3))
            cls.users.append(user)
        # A scored student in another university must never appear.
        earn(student("foreign", cls.w["civil"]), 5000, when=lagos(2026, 11, 3))
        cls.me = cls.users[46]

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.me)

    def get(self, path="university/lifetime", **params):
        r = self.client.get(f"{BASE}/{path}", params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_rank_47_sees_self_neighbours_and_top_10_with_defaults(self):
        body = self.get()
        self.assertEqual(body["me"]["rank"], 47)
        self.assertTrue(body["me"]["is_me"])
        self.assertEqual(body["me"]["xp"], 953)
        self.assertEqual(positions(body["top"]), list(range(1, 11)))
        self.assertEqual(positions(body["around_me"]), [45, 46, 47, 48, 49])
        self.assertEqual([e["is_me"] for e in body["around_me"]], [False, False, True, False, False])
        self.assertEqual(body["total"], 60)

    def test_top_survives_paging(self):
        body = self.get(offset=40, limit=10)
        self.assertEqual(positions(body["top"]), list(range(1, 11)))
        self.assertEqual(positions(body["entries"]), list(range(41, 51)))
        self.assertEqual(body["me"]["position"], 47)
        self.assertEqual(body["next_offset"], 50)

    def test_top_size_is_configurable_and_can_be_off(self):
        self.assertEqual(positions(self.get(top=3)["top"]), [1, 2, 3])
        self.assertEqual(self.get(top=0)["top"], [])

    def test_bad_top_is_a_field_error(self):
        for raw in ("-1", "101", "x"):
            with self.subTest(top=raw):
                r = self.client.get(f"{BASE}/university/lifetime", {"top": raw})
                self.assertEqual(r.status_code, 400)
                self.assertEqual(set(r.json()["field_errors"]), {"top"})

    def test_other_universities_never_appear_in_top(self):
        body = self.get(top=100)
        self.assertEqual(len(body["top"]), 60)
        self.assertNotIn("foreign", {e["user"]["username"] for e in body["top"]})
        self.assertEqual(body["top"][0]["user"]["id"], self.users[0].id)

    def test_one_board_query_per_response(self):
        with CaptureQueriesContext(connection) as ctx:
            body = self.get(offset=40, limit=10, top=10)
        board_queries = [q for q in ctx.captured_queries if "RANK() OVER" in q["sql"]]
        self.assertEqual(len(board_queries), 1)
        self.assertEqual(len(body["top"]) + len(body["entries"]) + len(body["around_me"]), 25)

    def test_viewer_off_the_board_still_gets_top(self):
        outsider = student("outsider", self.w["history"])
        self.client.force_authenticate(outsider)
        body = self.get()
        self.assertIsNone(body["me"])
        self.assertEqual(body["around_me"], [])
        self.assertEqual(positions(body["top"]), list(range(1, 11)))