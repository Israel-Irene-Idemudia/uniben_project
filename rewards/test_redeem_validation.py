import threading
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile
from rewards.models import Redemption


def _payload(**overrides):
    data = {"reward_type": "airtime", "phone": "08012345678", "network": "MTN"}
    data.update(overrides)
    return data


class RedeemCostTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", password="pass12345")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.points = 100
        self.profile.save()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("redeem-reward")

    def post(self, **overrides):
        return self.client.post(self.url, _payload(**overrides), format="json")

    def assertRejected(self, res):
        self.assertEqual(res.status_code, 400, res.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 100)
        self.assertEqual(Redemption.objects.count(), 0)

    def test_valid_cost_works(self):
        res = self.post(point_cost=50)
        self.assertEqual(res.status_code, 201, res.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 50)
        self.assertEqual(Redemption.objects.get().point_cost, 50)

    def test_negative_cost_is_rejected(self):
        self.assertRejected(self.post(point_cost=-100))

    def test_zero_cost_is_rejected(self):
        self.assertRejected(self.post(point_cost=0))

    def test_non_numeric_cost_is_rejected(self):
        for bad in ("abc", 1.9, True):
            with self.subTest(bad=bad):
                res = self.post(point_cost=bad)
                self.assertRejected(res)
                self.assertIn("point_cost", res.data)  # serializer error shape

    def test_cost_above_balance_is_rejected(self):
        res = self.post(point_cost=150)
        self.assertRejected(res)
        self.assertIn("error", res.data)

    def test_missing_cost_uses_default(self):
        res = self.client.post(self.url, _payload(), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 50)


@skipUnless(connection.vendor == "postgresql", "needs PostgreSQL row locking")
class RedeemConcurrencyTests(TransactionTestCase):
    def test_two_simultaneous_redeems_cannot_double_spend(self):
        user = get_user_model().objects.create_user(username="racer", password="pass12345")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.points = 100
        profile.save()
        url = reverse("redeem-reward")
        results = []
        barrier = threading.Barrier(2)

        def worker():
            try:
                client = APIClient()
                client.force_authenticate(user)
                barrier.wait()
                results.append(client.post(url, _payload(point_cost=60), format="json").status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sorted(results), [201, 400])
        profile.refresh_from_db()
        self.assertEqual(profile.points, 40)
        self.assertEqual(Redemption.objects.filter(user=user).count(), 1)