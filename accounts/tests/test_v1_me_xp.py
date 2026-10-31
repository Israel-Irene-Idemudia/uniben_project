"""/me and /me/progress read XP, level and balance from the XP ledger (Phase 3)."""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from xp.services import award_xp, get_balance, get_lifetime_xp, spend_points
from xp.tests.helpers import give_points, make_student


class MeXPIntegrationTests(TestCase):
    def setUp(self):
        self.user = make_student("ada", points=120)  # level 2 (100 XP threshold)
        self.other = make_student("bola", points=3000)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_me_shows_ledger_level_but_never_the_balance(self):
        body = self.client.get("/api/v1/me").json()
        self.assertEqual(body["xp_level"], 2)
        self.assertEqual(body["xp_level_title"], "Learner")
        self.assertNotIn("balance", body)
        self.assertNotIn("points", body)

    def test_progress_matches_the_ledger(self):
        body = self.client.get("/api/v1/me/progress").json()
        self.assertTrue(body["ledger_ready"])
        self.assertEqual(body["xp_total"], get_lifetime_xp(self.user))
        self.assertEqual(body["balance"], get_balance(self.user))
        self.assertEqual(body["xp_total"], 120)
        self.assertEqual(body["level"], 2)
        self.assertEqual(body["level_title"], "Learner")
        self.assertEqual(body["xp_to_next_level"], 130)  # next rung is 250

    def test_spending_lowers_balance_but_not_xp_or_level(self):
        # D-2: buying airtime must never drop a level.
        spend_points(
            self.user, cost=50, reason_code="reward", source_feature="rewards",
            idempotency_key="spend-test-1",
        )
        body = self.client.get("/api/v1/me/progress").json()
        self.assertEqual(body["balance"], 70)
        self.assertEqual(body["xp_total"], 120)
        self.assertEqual(body["level"], 2)
        self.assertEqual(self.client.get("/api/v1/me").json()["xp_level"], 2)

    def test_new_award_is_visible_immediately(self):
        award_xp(
            self.user, action_code="material_verified", source_feature="materials",
            source_record_id="m-1",
        )
        body = self.client.get("/api/v1/me/progress").json()
        self.assertEqual(body["xp_total"], 130)
        self.assertEqual(body["balance"], 130)

    def test_level_up_reflected(self):
        give_points(self.user, 200)  # 320 lifetime -> level 3
        self.assertEqual(self.client.get("/api/v1/me").json()["xp_level"], 3)
        self.assertEqual(self.client.get("/api/v1/me/progress").json()["xp_to_next_level"], 180)

    def test_legacy_points_field_is_ignored(self):
        # Someone tampers with the mirror: the API must still show the ledger.
        UserProfile.objects.filter(user=self.user).update(points=999999)
        body = self.client.get("/api/v1/me/progress").json()
        self.assertEqual(body["balance"], 120)
        self.assertEqual(body["xp_total"], 120)

    def test_each_student_sees_only_their_own_numbers(self):
        self.client.force_authenticate(self.other)
        body = self.client.get("/api/v1/me/progress").json()
        self.assertEqual(body["xp_total"], 3000)
        self.assertEqual(body["level"], 8)

    def test_student_without_profile_or_ledger_rows(self):
        from django.contrib.auth import get_user_model

        bare = get_user_model().objects.create_user("bare", "bare@test.com", "Pass#12345")
        self.client.force_authenticate(bare)
        me = self.client.get("/api/v1/me").json()
        progress = self.client.get("/api/v1/me/progress").json()
        self.assertEqual(me["xp_level"], 1)
        self.assertEqual(progress["xp_total"], 0)
        self.assertEqual(progress["xp_to_next_level"], 100)
        self.assertFalse(progress["profile_complete"])
