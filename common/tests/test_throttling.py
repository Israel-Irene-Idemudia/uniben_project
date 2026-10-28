from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from rest_framework.test import APIClient, APITestCase

from common.throttling import V1RateThrottle

RATES = V1RateThrottle.THROTTLE_RATES
PROTECTED = "/api/v1/_test/protected/"
PUBLIC = "/api/v1/_test/public/"
COMPETITIVE = "/api/v1/_test/competitive/"


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class V1ThrottleTests(APITestCase):
    def setUp(self):
        # Throttle counters live in the process-wide cache; start clean and
        # leave clean so other tests never see leftover counts.
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = get_user_model().objects.create_user("thr", password="x-Pass-12345")
        self.client.force_authenticate(self.user)

    def test_default_scope_blocks_after_the_limit(self):
        with mock.patch.dict(RATES, {"v1_default": "3/min"}):
            responses = [self.client.get(PROTECTED) for _ in range(4)]
        self.assertEqual([r.status_code for r in responses], [200, 200, 200, 429])
        blocked = responses[-1]
        self.assertEqual(blocked.data["code"], "rate_limited")
        self.assertIn("Retry-After", blocked)

    def test_each_user_has_their_own_bucket(self):
        other = get_user_model().objects.create_user("thr2", password="x-Pass-12345")
        other_client = APIClient()
        other_client.force_authenticate(other)
        with mock.patch.dict(RATES, {"v1_default": "2/min"}):
            for _ in range(2):
                self.client.get(PROTECTED)
            self.assertEqual(self.client.get(PROTECTED).status_code, 429)
            self.assertEqual(other_client.get(PROTECTED).status_code, 200)

    def test_scopes_do_not_share_a_bucket(self):
        with mock.patch.dict(RATES, {"v1_default": "2/min", "v1_competitive": "2/min"}):
            for _ in range(2):
                self.assertEqual(self.client.get(COMPETITIVE).status_code, 200)
            self.assertEqual(self.client.get(COMPETITIVE).status_code, 429)
            # Same user, other scope: still allowed.
            self.assertEqual(self.client.get(PROTECTED).status_code, 200)

    def test_anonymous_requests_are_limited_per_ip(self):
        anonymous = APIClient()
        with mock.patch.dict(RATES, {"v1_default": "2/min"}):
            codes = [anonymous.get(PUBLIC).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])


class LegacyViewsAreNotThrottledTests(SimpleTestCase):
    def test_no_global_throttle_classes_are_configured(self):
        self.assertNotIn("DEFAULT_THROTTLE_CLASSES", settings.REST_FRAMEWORK)

    def test_legacy_views_have_no_throttles(self):
        for path in ("/api/token/", "/api/rewards/redeem/"):
            with self.subTest(path=path):
                view_class = resolve(path).func.cls
                self.assertEqual(list(view_class.throttle_classes), [])