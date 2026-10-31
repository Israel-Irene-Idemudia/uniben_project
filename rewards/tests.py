"""Rewards API tests (rewritten in Phase 3: prices are server-owned, D-1 / D7)."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import UserProfile
from xp.models import XPLedgerEntry
from xp.services import get_balance
from xp.tests.helpers import make_admin, make_student

from .models import Redemption, RewardCatalog


class RewardsAPITests(APITestCase):
    def setUp(self):
        self.user = make_student("student", points=100)
        self.admin_user = make_admin("admin")
        RewardCatalog.objects.create(reward_type="500MB Data", point_cost=50)
        self.redeem_url = reverse('redeem-reward')
        self.redemptions_url = reverse('user-redemptions')
        self.admin_list_url = reverse('admin-redemptions-list')

    def test_redeem_reward_success_charges_the_catalogue_price(self):
        self.client.force_authenticate(user=self.user)
        payload = {'reward_type': '500MB Data', 'point_cost': 50, 'phone': '08012345678', 'network': 'MTN'}
        response = self.client.post(self.redeem_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.points, 50)  # mirror of the ledger
        self.assertEqual(get_balance(self.user), 50)
        self.assertEqual(profile.phone, '08012345678')
        self.assertEqual(profile.network, 'MTN')

        redemption = Redemption.objects.get()
        self.assertEqual(redemption.user, self.user)
        self.assertEqual(redemption.reward_type, '500MB Data')
        self.assertEqual(redemption.point_cost, 50)
        self.assertEqual(redemption.status, 'pending')
        self.assertEqual(redemption.ledger_entry.amount, -50)
        self.assertEqual(response.data['point_cost'], 50)  # legacy response shape kept

    def test_redeem_reward_insufficient_points(self):
        RewardCatalog.objects.create(reward_type="Big Data", point_cost=150)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.redeem_url, {'reward_type': 'Big Data', 'phone': '0801', 'network': 'MTN'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(get_balance(self.user), 100)
        self.assertEqual(Redemption.objects.count(), 0)

    def test_user_list_redemptions(self):
        Redemption.objects.create(user=self.user, reward_type='250MB Data', point_cost=30, phone='08000000', network='Airtel')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.redemptions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['reward_type'], '250MB Data')

    def test_admin_list_and_dispatch_redemptions(self):
        redemption = Redemption.objects.create(
            user=self.user, reward_type='1GB Data', point_cost=100, phone='0801234', network='Glo'
        )
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.get(self.admin_list_url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.admin_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        dispatch_url = reverse('admin-redemptions-dispatch', kwargs={'pk': redemption.pk})
        response = self.client.patch(dispatch_url, {'status': 'dispatched'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        redemption.refresh_from_db()
        self.assertEqual(redemption.status, 'dispatched')
