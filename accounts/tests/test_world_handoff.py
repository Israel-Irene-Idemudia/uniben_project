import hashlib
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import UserProfile, WorldHandoffToken
from common.models import AuditLog
from common.services import set_setting
from common.throttling import V1RateThrottle

User = get_user_model()
CREATE = "/api/v1/auth/world-handoff"
EXCHANGE = "/api/v1/auth/world-handoff/exchange"


class WorldHandoffTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user("stu", "stu@example.com", "Pass#12345")
        UserProfile.objects.create(user=self.user)
        self.admin_user = User.objects.create_superuser("root", "r@example.com", "Pass#12345")

    def _create(self, user=None):
        self.client.force_authenticate(user or self.user)
        response = self.client.post(CREATE, {}, format="json")
        self.client.force_authenticate(None)
        return response

    def _exchange(self, token):
        return self.client.post(EXCHANGE, {"token": token}, format="json")

    def test_create_requires_authentication(self):
        r = self.client.post(CREATE, {}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "not_authenticated")

    def test_create_returns_a_key_and_its_lifetime_and_is_not_cached(self):
        r = self._create()
        self.assertEqual(r.status_code, 201)
        body = r.json()
        self.assertEqual(body["expires_in"], 60)
        self.assertGreaterEqual(len(body["token"]), 40)
        self.assertEqual(r["Cache-Control"], "no-store")

    def test_only_a_hash_of_the_key_is_stored(self):
        raw = self._create().json()["token"]
        row = WorldHandoffToken.objects.get()
        self.assertEqual(row.token_hash, hashlib.sha256(raw.encode()).hexdigest())
        self.assertNotEqual(row.token_hash, raw)
        self.assertEqual(len(row.token_hash), 64)

    def test_exchange_gives_a_working_session_for_the_same_student(self):
        raw = self._create().json()["token"]
        r = self._exchange(raw)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["user"]["username"], "stu")
        self.assertEqual(r["Cache-Control"], "no-store")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {body['access']}")
        me = self.client.get("/api/v1/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["username"], "stu")

    def test_each_key_opens_only_its_own_students_session(self):
        other = User.objects.create_user("other", "o@example.com", "Pass#12345")
        UserProfile.objects.create(user=other)
        raw_other = self._create(other).json()["token"]
        self.assertEqual(self._exchange(raw_other).json()["user"]["username"], "other")

    def test_a_key_works_only_once(self):
        raw = self._create().json()["token"]
        self.assertEqual(self._exchange(raw).status_code, 200)
        r = self._exchange(raw)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "bad_request")

    def test_an_expired_key_is_rejected(self):
        raw = self._create().json()["token"]
        WorldHandoffToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self._exchange(raw).status_code, 400)

    def test_every_failure_gives_the_same_message(self):
        used = self._create().json()["token"]
        self._exchange(used)
        messages = {
            self._exchange(used).json()["message"],
            self._exchange("not-a-real-key").json()["message"],
        }
        self.assertEqual(len(messages), 1)

    def test_missing_token_is_a_field_error(self):
        r = self.client.post(EXCHANGE, {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "validation_error")
        self.assertIn("token", r.json()["field_errors"])

    def test_an_inactive_account_cannot_exchange(self):
        raw = self._create().json()["token"]
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self._exchange(raw).status_code, 400)

    def test_exchange_ignores_a_bad_authorization_header(self):
        raw = self._create().json()["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer junk")
        self.assertEqual(self._exchange(raw).status_code, 200)

    def test_create_and_exchange_are_audited(self):
        raw = self._create().json()["token"]
        self._exchange(raw)
        created = AuditLog.objects.get(action="auth.handoff_created")
        exchanged = AuditLog.objects.get(action="auth.handoff_exchanged")
        self.assertEqual(created.actor, self.user)
        self.assertEqual(exchanged.actor, self.user)
        self.assertNotIn(raw, str(created.after) + str(exchanged.after))

    def test_lifetime_comes_from_the_setting_and_is_kept_in_range(self):
        for stored, expected in ((30, 30), (5, 10), (9999, 300), ("abc", 60)):
            set_setting("auth.handoff_ttl_seconds", stored, actor=self.admin_user, reason="test")
            self.assertEqual(self._create().json()["expires_in"], expected)

    def test_creating_keys_is_rate_limited(self):
        with mock.patch.dict(V1RateThrottle.THROTTLE_RATES, {"v1_auth": "2/min"}):
            codes = [self._create().status_code for _ in range(3)]
        self.assertEqual(codes, [201, 201, 429])