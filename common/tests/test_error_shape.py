import logging
import uuid

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient, APITestCase

from common.request_context import (
    RequestIDFilter,
    get_request_id,
    reset_request_id,
    set_request_id,
)

SHAPE_KEYS = {"code", "message", "field_errors", "request_id"}


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class V1ErrorShapeTests(APITestCase):
    base = "/api/v1/_test/"

    def setUp(self):
        self.user = get_user_model().objects.create_user("shape", password="x-Pass-12345")

    def login(self):
        self.client.force_authenticate(self.user)

    def assert_shape(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(set(response.data.keys()), SHAPE_KEYS)
        self.assertEqual(response.data["code"], code)
        self.assertTrue(response.data["request_id"])

    def test_validation_error_has_field_errors(self):
        self.login()
        response = self.client.post(self.base + "validate/", {}, format="json")
        self.assert_shape(response, 400, "validation_error")
        self.assertEqual(response.data["field_errors"], {"name": ["This field is required."]})

    def test_unauthenticated_is_401(self):
        response = self.client.get(self.base + "protected/")
        self.assert_shape(response, 401, "not_authenticated")

    def test_invalid_token_keeps_jwt_code(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        response = self.client.get(self.base + "protected/")
        self.assert_shape(response, 401, "token_not_valid")

    def test_permission_denied_is_403(self):
        self.login()
        response = self.client.get(self.base + "forbidden/")
        self.assert_shape(response, 403, "permission_denied")
        self.assertEqual(response.data["message"], "You cannot do that.")

    def test_missing_object_is_404(self):
        self.login()
        response = self.client.get(self.base + "notfound/")
        self.assert_shape(response, 404, "not_found")

    def test_conflict_is_409(self):
        self.login()
        response = self.client.get(self.base + "conflict/")
        self.assert_shape(response, 409, "conflict")

    def test_throttled_is_429_with_retry_after(self):
        self.login()
        response = self.client.get(self.base + "throttled/")
        self.assert_shape(response, 429, "rate_limited")
        self.assertEqual(response["Retry-After"], "5")

    def test_unhandled_error_is_500_and_hides_the_cause(self):
        self.login()
        with self.assertLogs("common.exceptions", level="ERROR"):
            response = self.client.get(self.base + "boom/")
        self.assert_shape(response, 500, "server_error")
        self.assertNotIn("secret", response.content.decode())

    def test_body_request_id_matches_response_header(self):
        response = self.client.get(self.base + "protected/")
        self.assertEqual(response.data["request_id"], response["X-Request-ID"])


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class RequestIDMiddlewareTests(APITestCase):
    url = "/api/v1/_test/public/"

    def test_safe_incoming_id_is_echoed(self):
        response = self.client.get(self.url, HTTP_X_REQUEST_ID="client-abc_123.x")
        self.assertEqual(response["X-Request-ID"], "client-abc_123.x")

    def test_unsafe_incoming_id_is_replaced(self):
        response = self.client.get(self.url, HTTP_X_REQUEST_ID="bad value!")
        uuid.UUID(response["X-Request-ID"])

    def test_overlong_incoming_id_is_replaced(self):
        response = self.client.get(self.url, HTTP_X_REQUEST_ID="a" * 65)
        uuid.UUID(response["X-Request-ID"])

    def test_id_is_generated_when_none_sent(self):
        response = self.client.get(self.url)
        uuid.UUID(response["X-Request-ID"])

    def test_context_is_cleared_after_the_request(self):
        self.client.get(self.url)
        self.assertIsNone(get_request_id())


class RequestIDFilterTests(SimpleTestCase):
    def _record(self):
        return logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)

    def test_filter_adds_current_request_id(self):
        token = set_request_id("req-1")
        try:
            record = self._record()
            RequestIDFilter().filter(record)
        finally:
            reset_request_id(token)
        self.assertEqual(record.request_id, "req-1")

    def test_filter_uses_dash_outside_a_request(self):
        record = self._record()
        RequestIDFilter().filter(record)
        self.assertEqual(record.request_id, "-")


class LegacyResponsesUnchangedTests(APITestCase):
    """The v1 error shape must not leak onto legacy routes (API-05, D-11)."""

    def test_legacy_error_body_is_not_the_v1_shape(self):
        response = APIClient().post("/api/rewards/redeem/", {}, format="json")
        self.assertIn(response.status_code, (401, 403))
        self.assertIn("detail", response.data)
        self.assertNotIn("code", response.data)
        self.assertNotIn("request_id", response.data)

    def test_legacy_responses_still_carry_the_request_id_header(self):
        response = APIClient().post("/api/rewards/redeem/", {}, format="json")
        self.assertTrue(response["X-Request-ID"])