from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.lockout import (
    failure_count,
    lock_seconds_remaining,
    lockout_schedule,
    lockout_threshold,
    login_key,
    purge_old_events,
)
from accounts.models import AuthEvent, UserProfile
from common.services import set_setting

User = get_user_model()
LOGIN = "/api/token/"
GOOD = "Pass#12345"


class LoginLockoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("stu", "stu@example.com", GOOD)
        UserProfile.objects.create(user=self.user)
        self.other = User.objects.create_user("other", "o@example.com", GOOD)
        UserProfile.objects.create(user=self.other)
        self.admin_user = User.objects.create_superuser("root", "r@example.com", GOOD)

    def _login(self, name="stu", password=GOOD):
        return self.client.post(LOGIN, {"username": name, "password": password}, format="json")

    def _bad(self, name="stu", times=1):
        return [self._login(name, "wrong-password") for _ in range(times)][-1]

    def _failures(self, key, n, minutes_ago=0):
        ids = [
            AuthEvent.objects.create(
                kind=AuthEvent.KIND_LOGIN, key_hash=key, success=False, detail="bad_credentials"
            ).pk
            for _ in range(n)
        ]
        if minutes_ago:
            AuthEvent.objects.filter(pk__in=ids).update(
                created_at=timezone.now() - timedelta(minutes=minutes_ago)
            )

    # --- behaviour through the real login endpoint ---

    def test_a_normal_login_keeps_its_old_shape(self):
        r = self._login()
        self.assertEqual(r.status_code, 200)
        for key in ("access", "refresh", "username", "email", "is_staff", "points"):
            self.assertIn(key, r.json())

    def test_five_failures_then_even_the_right_password_is_refused(self):
        self._bad(times=5)
        r = self._login()  # correct password, but locked
        self.assertEqual(r.status_code, 429)
        self.assertIn("Too many failed attempts", r.json()["detail"])
        self.assertTrue(r["Retry-After"].isdigit())

    def test_a_success_resets_the_count(self):
        self._bad(times=4)
        self.assertEqual(self._login().status_code, 200)
        self._bad(times=4)
        self.assertEqual(self._login().status_code, 200)  # only 4 since the last success

    def test_other_accounts_are_not_affected(self):
        self._bad(times=5)
        self.assertEqual(self._login("other").status_code, 200)

    def test_email_and_username_share_one_count(self):
        self._bad("stu", times=3)
        self._bad("stu@example.com", times=2)
        self.assertEqual(self._login("stu").status_code, 429)
        self.assertEqual(self._login("stu@example.com").status_code, 429)

    def test_unknown_names_lock_exactly_like_real_ones(self):
        ghost = self._bad("ghost", times=5)
        real = self._bad("stu", times=5)
        self.assertEqual(ghost.status_code, real.status_code)  # same failure body
        self.assertEqual(ghost.json(), real.json())
        locked_ghost = self._login("ghost")
        locked_real = self._login("stu")
        self.assertEqual(locked_ghost.status_code, 429)
        self.assertEqual(locked_ghost.json(), locked_real.json())

    def test_attempts_made_while_locked_do_not_extend_the_lock(self):
        self._bad(times=5)
        key, _ = login_key("stu")
        for _ in range(3):
            self.assertEqual(self._login().status_code, 429)
        self.assertEqual(failure_count(key), 5)

    def test_missing_username_is_a_plain_400_and_is_not_logged(self):
        r = self.client.post(LOGIN, {"password": "x"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(AuthEvent.objects.count(), 0)

    # --- the auth log ---

    def test_events_are_logged_without_the_plain_name(self):
        self._bad()
        bad = AuthEvent.objects.get(kind=AuthEvent.KIND_LOGIN)
        self.assertFalse(bad.success)
        self.assertEqual(bad.detail, "bad_credentials")
        self.assertEqual(bad.user, self.user)
        self.assertEqual(bad.ip_address, "127.0.0.1")
        self.assertEqual(len(bad.key_hash), 64)
        self.assertNotIn("stu", bad.key_hash)
        self._login()
        self.assertTrue(AuthEvent.objects.filter(success=True, user=self.user).exists())

    def test_locked_attempts_are_logged_as_locked(self):
        self._bad(times=5)
        self._login()
        self.assertTrue(AuthEvent.objects.filter(detail="locked").exists())

    def test_events_older_than_90_days_are_purged(self):
        old = AuthEvent.objects.create(kind=AuthEvent.KIND_LOGIN, key_hash="a")
        new = AuthEvent.objects.create(kind=AuthEvent.KIND_LOGIN, key_hash="b")
        AuthEvent.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=100))
        self.assertEqual(purge_old_events(), 1)
        self.assertFalse(AuthEvent.objects.filter(pk=old.pk).exists())
        self.assertTrue(AuthEvent.objects.filter(pk=new.pk).exists())

    # --- the escalation schedule (checked directly: no need for dozens of logins) ---

    def test_schedule_escalates_and_caps(self):
        key, _ = login_key("stu")
        cases = [(4, 0, 0), (5, 1, 60), (6, 1, 60), (7, 240, 300), (9, 840, 900), (11, 3540, 3600), (30, 3540, 3600)]
        for count, low, high in cases:
            AuthEvent.objects.all().delete()
            self._failures(key, count)
            remaining = lock_seconds_remaining(key)
            if high == 0:
                self.assertEqual(remaining, 0, count)
            else:
                self.assertTrue(low < remaining <= high, (count, remaining))

    def test_a_lock_expires(self):
        key, _ = login_key("stu")
        self._failures(key, 5, minutes_ago=2)
        self.assertEqual(lock_seconds_remaining(key), 0)

    def test_old_failures_are_forgiven_after_a_day(self):
        key, _ = login_key("stu")
        self._failures(key, 9, minutes_ago=60 * 25)
        self.assertEqual(failure_count(key), 0)

    # --- settings ---

    def test_threshold_and_schedule_come_from_settings(self):
        set_setting("auth.lockout_threshold", 3, actor=self.admin_user, reason="test")
        self.assertEqual(lockout_threshold(), 3)
        self._bad(times=3)
        self.assertEqual(self._login().status_code, 429)
        set_setting("auth.lockout_schedule_minutes", [2, 3], actor=self.admin_user, reason="test")
        self.assertEqual(lockout_schedule(), [2, 3])

    def test_unusable_settings_fall_back_to_the_defaults(self):
        set_setting("auth.lockout_threshold", "abc", actor=self.admin_user, reason="test")
        set_setting("auth.lockout_schedule_minutes", [0, "x"], actor=self.admin_user, reason="test")
        self.assertEqual(lockout_threshold(), 5)
        self.assertEqual(lockout_schedule(), [1, 5, 15, 60])