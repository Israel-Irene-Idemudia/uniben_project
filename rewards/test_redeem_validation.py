"""Redeem rules (Phase 3): the server owns prices; a client can never mint
points or underpay. Replaces the old tests that trusted a client point_cost."""
import threading
from unittest import skipUnless

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile
from xp.models import XPLedgerEntry
from xp.services import get_balance
from xp.tests.helpers import make_student

from .models import Redemption, RewardCatalog


def _payload(**overrides):
    data = {"reward_type": "airtime", "phone": "08012345678", "network": "MTN"}
    data.update(overrides)
    return data


class LegacyRedeemPriceTests(TestCase):
    def setUp(self):
        self.user = make_student("tester", points=100)
        RewardCatalog.objects.create(reward_type="airtime", point_cost=50)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("redeem-reward")

    def post(self, **overrides):
        return self.client.post(self.url, _payload(**overrides), format="json")

    def test_client_sent_price_is_ignored_every_time(self):
        for bad in (1, 0, -100, 9999, "abc", 1.9, True):
            with self.subTest(bad=bad):
                before = get_balance(self.user)
                if before < 50:
                    break
                res = self.post(point_cost=bad)
                self.assertEqual(res.status_code, 201, res.data)
                self.assertEqual(res.data["point_cost"], 50)
                self.assertEqual(get_balance(self.user), before - 50)

    def test_missing_price_is_charged_the_catalogue_price(self):
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(UserProfile.objects.get(user=self.user).points, 50)

    def test_unknown_or_inactive_reward_is_refused_and_nothing_moves(self):
        RewardCatalog.objects.create(reward_type="retired", point_cost=10, is_active=False)
        for name in ("not-a-reward", "retired", ""):
            with self.subTest(name=name):
                res = self.post(reward_type=name)
                self.assertEqual(res.status_code, 400)
        self.assertEqual(get_balance(self.user), 100)
        self.assertEqual(Redemption.objects.count(), 0)

    def test_cannot_spend_more_than_the_balance(self):
        RewardCatalog.objects.create(reward_type="huge", point_cost=500)
        res = self.post(reward_type="huge")
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.data)
        self.assertEqual(get_balance(self.user), 100)
        self.assertEqual(Redemption.objects.count(), 0)
        self.assertEqual(XPLedgerEntry.objects.filter(kind="spend").count(), 0)

    def test_missing_phone_or_network_is_a_serializer_error(self):
        res = self.client.post(self.url, {"reward_type": "airtime"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("phone", res.data)


class V1RedeemTests(TestCase):
    def setUp(self):
        self.user = make_student("v1user", points=120)
        RewardCatalog.objects.create(reward_type="airtime", point_cost=50)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = "/api/v1/rewards/redeem"

    def test_idempotency_key_is_required(self):
        res = self.client.post(self.url, _payload(), format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(get_balance(self.user), 120)

    def test_retrying_with_the_same_key_charges_once(self):
        first = self.client.post(self.url, _payload(), format="json", headers={"Idempotency-Key": "abc-1"})
        second = self.client.post(self.url, _payload(), format="json", headers={"Idempotency-Key": "abc-1"})
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(second["Idempotent-Replayed"], "true")
        self.assertEqual(Redemption.objects.count(), 1)
        self.assertEqual(get_balance(self.user), 70)

    def test_a_new_key_is_a_new_redemption(self):
        self.client.post(self.url, _payload(), format="json", headers={"Idempotency-Key": "k1"})
        self.client.post(self.url, _payload(), format="json", headers={"Idempotency-Key": "k2"})
        self.assertEqual(get_balance(self.user), 20)

    def test_client_price_is_ignored_and_errors_do_not_burn_the_key(self):
        res = self.client.post(self.url, _payload(point_cost=1), format="json", headers={"Idempotency-Key": "k"})
        self.assertEqual(res.data["point_cost"], 50)
        bad = self.client.post(self.url, _payload(reward_type="nope"), format="json", headers={"Idempotency-Key": "k2"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(get_balance(self.user), 70)

    def test_insufficient_points_is_400_and_rolls_back(self):
        RewardCatalog.objects.create(reward_type="huge", point_cost=500)
        res = self.client.post(self.url, _payload(reward_type="huge"), format="json", headers={"Idempotency-Key": "k"})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Redemption.objects.count(), 0)
        self.assertEqual(get_balance(self.user), 120)

    def test_catalog_lists_only_active_rewards(self):
        RewardCatalog.objects.create(reward_type="retired", point_cost=5, is_active=False)
        res = self.client.get("/api/v1/rewards/catalog")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([r["reward_type"] for r in res.data["results"]], ["airtime"])

    def test_my_redemptions_are_mine_only(self):
        other = make_student("other", points=100)
        self.client.post(self.url, _payload(), format="json", headers={"Idempotency-Key": "mine"})
        other_client = APIClient()
        other_client.force_authenticate(other)
        res = other_client.get("/api/v1/rewards/redemptions")
        self.assertEqual(res.data["results"], [])
        self.assertEqual(len(self.client.get("/api/v1/rewards/redemptions").data["results"]), 1)

    def test_requires_login(self):
        res = APIClient().post(self.url, _payload(), format="json", headers={"Idempotency-Key": "x"})
        self.assertIn(res.status_code, (401, 403))


@skipUnless(connection.vendor == "postgresql", "needs PostgreSQL row locking")
class RedeemConcurrencyTests(TransactionTestCase):
    """SQLite cannot prove row locking. Run this on PostgreSQL (Israel)."""

    def test_two_simultaneous_redeems_cannot_double_spend(self):
        user = make_student("racer", points=100)
        RewardCatalog.objects.create(reward_type="airtime", point_cost=60)
        url = reverse("redeem-reward")
        results = []
        barrier = threading.Barrier(2)

        def worker():
            try:
                client = APIClient()
                client.force_authenticate(user)
                barrier.wait()
                results.append(client.post(url, _payload(), format="json").status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sorted(results), [201, 400])
        self.assertEqual(get_balance(user), 40)
        self.assertEqual(Redemption.objects.filter(user=user).count(), 1)
