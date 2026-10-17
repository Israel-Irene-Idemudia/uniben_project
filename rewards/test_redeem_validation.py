from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import UserProfile


class RedeemCostTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="tester", password="pass12345")
        self.profile, _ = UserProfile.objects.get_or_create(user=user)
        self.profile.points = 100
        self.profile.save()
        self.client = APIClient()
        self.client.force_authenticate(user)

    def redeem(self, cost):
        return self.client.post(
            "/api/rewards/redeem/",
            {"reward_type": "airtime", "phone": "08012345678",
             "network": "MTN", "point_cost": cost},
            format="json",
        )

    def test_valid_cost_works(self):
        # Control test: proves the payload itself is valid
        res = self.redeem(50)
        self.profile.refresh_from_db()
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self.profile.points, 50)

    def test_negative_cost_is_rejected(self):
        res = self.redeem(-100)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 100,
                         f"Points became {self.profile.points} (HTTP {res.status_code})")

    def test_zero_cost_is_rejected(self):
        res = self.redeem(0)
        self.assertGreaterEqual(res.status_code, 400, f"HTTP {res.status_code}")