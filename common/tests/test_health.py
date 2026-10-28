from unittest import mock

from django.core.cache import cache
from django.db import OperationalError
from rest_framework.test import APITestCase

from common.throttling import V1RateThrottle

HEALTH = "/api/v1/health"
READY = "/api/v1/ready"


class HealthTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_health_is_public_and_ok(self):
        response = self.client.get(HEALTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    def test_health_touches_no_database(self):
        with self.assertNumQueries(0):
            self.client.get(HEALTH)

    def test_trailing_slash_is_accepted(self):
        self.assertEqual(self.client.get(HEALTH + "/").status_code, 200)
        self.assertEqual(self.client.get(READY + "/").status_code, 200)

    def test_a_bad_token_cannot_break_a_public_check(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(self.client.get(HEALTH).status_code, 200)
        self.assertEqual(self.client.get(READY).status_code, 200)

    def test_health_and_ready_are_not_throttled(self):
        with mock.patch.dict(V1RateThrottle.THROTTLE_RATES, {"v1_default": "1/min"}):
            codes = [self.client.get(HEALTH).status_code for _ in range(3)]
            codes += [self.client.get(READY).status_code for _ in range(3)]
        self.assertEqual(codes, [200] * 6)

    def test_ready_is_ok_when_the_database_answers(self):
        response = self.client.get(READY)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ready"})

    def test_ready_is_503_in_the_v1_error_shape_when_the_database_is_down(self):
        with mock.patch("common.health.connection") as fake:
            fake.cursor.side_effect = OperationalError("db down")
            with self.assertLogs("common.health", level="ERROR"):
                response = self.client.get(READY)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "service_unavailable")
        self.assertEqual(response.data["message"], "Database is unavailable.")
        self.assertTrue(response.data["request_id"])

    def test_ready_does_not_leak_the_underlying_error(self):
        with mock.patch("common.health.connection") as fake:
            fake.cursor.side_effect = OperationalError("secret db host name")
            with self.assertLogs("common.health", level="ERROR"):
                response = self.client.get(READY)
        self.assertNotIn("secret", response.content.decode())