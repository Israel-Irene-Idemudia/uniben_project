from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import UserProfile
from .models import Redemption

User = get_user_model()

class RewardsAPITests(APITestCase):
    def setUp(self):
        # Create regular user
        self.user = User.objects.create_user(username='student', password='password123', email='student@test.com')
        self.profile = UserProfile.objects.create(user=self.user, points=100)

        # Create admin user
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpassword', email='admin@test.com')
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, points=0)

        # URLs
        self.redeem_url = reverse('redeem-reward')
        self.redemptions_url = reverse('user-redemptions')
        self.admin_list_url = reverse('admin-redemptions-list')

    def test_redeem_reward_success(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'reward_type': '500MB Data',
            'point_cost': 50,
            'phone': '08012345678',
            'network': 'MTN'
        }
        response = self.client.post(self.redeem_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify points deducted
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 50)
        self.assertEqual(self.profile.phone, '08012345678')
        self.assertEqual(self.profile.network, 'MTN')

        # Verify redemption record
        self.assertEqual(Redemption.objects.count(), 1)
        redemption = Redemption.objects.first()
        self.assertEqual(redemption.user, self.user)
        self.assertEqual(redemption.reward_type, '500MB Data')
        self.assertEqual(redemption.point_cost, 50)
        self.assertEqual(redemption.status, 'pending')

    def test_redeem_reward_insufficient_points(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'reward_type': '500MB Data',
            'point_cost': 150,  # User only has 100
            'phone': '08012345678',
            'network': 'MTN'
        }
        response = self.client.post(self.redeem_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # Points should not change
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 100)

    def test_user_list_redemptions(self):
        # Create a pre-existing redemption
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

        # Unauthorized access
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.admin_list_url)
        self.assertEqual(response.status_code, status.HTTP_430_FORBIDDEN if hasattr(status, 'HTTP_430_FORBIDDEN') else status.HTTP_403_FORBIDDEN) # Let's handle forbidden response check
        
        # Admin access
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.admin_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Dispatch
        dispatch_url = reverse('admin-redemptions-dispatch', kwargs={'pk': redemption.pk})
        response = self.client.patch(dispatch_url, {'status': 'dispatched'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        redemption.refresh_from_db()
        self.assertEqual(redemption.status, 'dispatched')
