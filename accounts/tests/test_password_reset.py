from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework.test import APITestCase

from accounts.models import AuthEvent
from accounts.password_reset_views import (
    CONFIRM_FAILURES_PER_HOUR,
    REQUESTS_PER_EMAIL_PER_HOUR,
)

User = get_user_model()
URL = "/api/password_reset/"
NEW_PASSWORD = "BrandNewPass#2026"


class PasswordResetHardeningTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("stu", "stu@example.com", "OldPass#12345")

    def _request_code(self):
        r = self.client.post(URL, {"email": "stu@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        return ResetPasswordToken.objects.get(user=self.user)

    def test_code_is_five_digits_and_flow_still_works(self):
        token = self._request_code()
        self.assertRegex(token.key, r"^\d{5}$")
        r = self.client.post(URL + "confirm/", {"token": token.key, "password": NEW_PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_request_limit_per_email(self):
        for _ in range(REQUESTS_PER_EMAIL_PER_HOUR):
            self._request_code()
        r = self.client.post(URL, {"email": "STU@example.com "}, format="json")  # case/space variant
        self.assertEqual(r.status_code, 429)

    def test_guess_limit_blocks_even_a_correct_code(self):
        token = self._request_code()
        AuthEvent.objects.bulk_create(
            [AuthEvent(kind=AuthEvent.KIND_RESET_CONFIRM, success=False)] * CONFIRM_FAILURES_PER_HOUR
        )
        r = self.client.post(URL + "confirm/", {"token": token.key, "password": NEW_PASSWORD}, format="json")
        self.assertEqual(r.status_code, 429)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass#12345"))

    def test_wrong_code_is_recorded_and_returns_library_error(self):
        self._request_code()
        r = self.client.post(URL + "confirm/", {"token": "00000", "password": NEW_PASSWORD}, format="json")
        self.assertIn(r.status_code, (400, 404))
        self.assertEqual(AuthEvent.objects.filter(kind=AuthEvent.KIND_RESET_CONFIRM, success=False).count(), 1)

    def test_code_expires_after_15_minutes(self):
        token = self._request_code()
        ResetPasswordToken.objects.filter(pk=token.pk).update(
            created_at=timezone.now() - timedelta(minutes=20)
        )
        r = self.client.post(URL + "confirm/", {"token": token.key, "password": NEW_PASSWORD}, format="json")
        self.assertIn(r.status_code, (400, 404))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass#12345"))

    def test_re_request_refreshes_expiry(self):
        token = self._request_code()
        ResetPasswordToken.objects.filter(pk=token.pk).update(
            created_at=timezone.now() - timedelta(minutes=12)
        )
        token = self._request_code()
        self.assertLess(timezone.now() - token.created_at, timedelta(minutes=1))