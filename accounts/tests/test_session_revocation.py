from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.handoff import create_handoff_token
from accounts.models import UserProfile
from accounts.session_revocation import revoke_all_sessions
from common.models import AuditLog

User = get_user_model()
REFRESH = "/api/token/refresh/"
NEW_PASSWORD = "BrandNewPass#2026"


class SessionRevocationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = User.objects.create_user("stu", "stu@example.com", "Pass#12345")
        UserProfile.objects.create(user=self.user)
        self.admin_user = User.objects.create_superuser("root", "r@example.com", "Pass#12345")

    def _new_refresh(self, user=None):
        return str(RefreshToken.for_user(user or self.user))

    def _refresh_status(self, token):
        # Each successful refresh rotates (and so uses up) the token it was given.
        return self.client.post(REFRESH, {"refresh": token}, format="json").status_code

    def test_a_refresh_token_works_normally(self):
        self.assertEqual(self._refresh_status(self._new_refresh()), 200)

    def test_a_password_change_revokes_every_refresh_token(self):
        first, second = self._new_refresh(), self._new_refresh()
        self.user.set_password("Another#Pass2026")
        self.user.save()
        self.assertEqual(self._refresh_status(first), 401)
        self.assertEqual(self._refresh_status(second), 401)

    def test_other_students_are_not_signed_out(self):
        other = User.objects.create_user("other", "o@example.com", "Pass#12345")
        keep = self._new_refresh(other)
        self.user.set_password("Another#Pass2026")
        self.user.save()
        self.assertEqual(self._refresh_status(keep), 200)

    def test_an_unrelated_save_keeps_sessions(self):
        token = self._new_refresh()
        self.user.first_name = "Ada"
        self.user.save()
        self.user.save(update_fields=["last_login"])
        self.assertEqual(self._refresh_status(token), 200)

    def test_a_hash_upgrade_at_login_is_not_a_password_change(self):
        self.user.password = make_password("Pass#12345", hasher="pbkdf2_sha1")  # an older hash
        self.user.save()
        token = self._new_refresh()  # issued AFTER the old hash was stored
        self.assertTrue(self.user.check_password("Pass#12345"))  # Django upgrades the hash now
        self.assertFalse(self.user.password.startswith("pbkdf2_sha1$"))
        self.assertEqual(self._refresh_status(token), 200)

    def test_the_password_reset_flow_signs_the_student_out(self):
        token = self._new_refresh()
        self.assertEqual(
            self.client.post("/api/password_reset/", {"email": "stu@example.com"}, format="json").status_code, 200
        )
        code = ResetPasswordToken.objects.get(user=self.user).key
        r = self.client.post(
            "/api/password_reset/confirm/", {"token": code, "password": NEW_PASSWORD}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._refresh_status(token), 401)

    def test_logging_in_with_the_new_password_still_works(self):
        self.user.set_password(NEW_PASSWORD)
        self.user.save()
        r = self.client.post("/api/token/", {"username": "stu", "password": NEW_PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._refresh_status(r.json()["refresh"]), 200)

    def test_revocation_is_audited_with_a_count(self):
        self._new_refresh()
        self._new_refresh()
        self.user.set_password("Another#Pass2026")
        self.user.save()
        log = AuditLog.objects.get(action="auth.sessions_revoked", target_id=str(self.user.pk))
        self.assertEqual(log.after["revoked_refresh_tokens"], 2)
        self.assertEqual(log.reason, "Password changed")

    def test_the_service_can_run_twice(self):
        self._new_refresh()
        self._new_refresh()
        self.assertEqual(revoke_all_sessions(self.user, reason="test"), 2)
        self.assertEqual(revoke_all_sessions(self.user, reason="test"), 0)

    def test_unused_handoff_keys_die_with_the_password(self):
        raw, _ = create_handoff_token(self.user)
        self.user.set_password("Another#Pass2026")
        self.user.save()
        r = self.client.post("/api/v1/auth/world-handoff/exchange", {"token": raw}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_an_admin_can_sign_a_student_out_everywhere(self):
        token = self._new_refresh()
        self.client.force_login(self.admin_user)
        r = self.client.post(
            "/admin/tps/auth/user/",
            {"action": "sign_out_everywhere", "_selected_action": [self.user.pk]},
        )
        self.assertEqual(r.status_code, 302)
        self.client.logout()
        self.assertEqual(self._refresh_status(token), 401)
        log = AuditLog.objects.get(action="auth.sessions_revoked", target_id=str(self.user.pk))
        self.assertEqual(log.actor, self.admin_user)