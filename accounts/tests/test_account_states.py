from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, APITestCase, force_authenticate
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.account_state import anonymise_user, get_account_state, set_account_state
from accounts.models import (
    AccountDeletionRequest,
    AccountStatus,
    AuthEvent,
    StudentDepartmentHistory,
    UserDebaterProgress,
    UserGpaEntry,
    UserNoteEntry,
    UserPreferences,
    UserProfile,
    UserTimetableEntry,
    UserTodoEntry,
)
from accounts.permissions import IsNotSuspended
from common.models import AuditLog
from common.views import V1APIView
from core.models import ContactMessage, Department, Faculty

User = get_user_model()
PASSWORD = "Pass#12345"


class _Dummy(V1APIView):
    permission_classes = [IsAuthenticated, IsNotSuspended]

    def get(self, request):
        return Response({"ok": True})


def _call(user):
    request = APIRequestFactory().get("/x")
    if user is not None:
        force_authenticate(request, user=user)
    return _Dummy.as_view()(request)


class AccountStateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("stu", "stu@example.com", PASSWORD)
        UserProfile.objects.create(user=self.user)
        self.admin_user = User.objects.create_superuser("root", "r@example.com", PASSWORD)

    def test_no_row_means_active(self):
        self.assertEqual(get_account_state(self.user), "active")

    def test_suspend_and_reinstate_are_audited_with_a_reason(self):
        set_account_state(self.user, "suspended", actor=self.admin_user, reason="Abuse report 12")
        self.assertEqual(get_account_state(self.user), "suspended")
        log = AuditLog.objects.get(action="account.suspended")
        self.assertEqual(log.before, {"state": "active"})
        self.assertEqual(log.after, {"state": "suspended"})
        self.assertEqual(log.reason, "Abuse report 12")
        self.assertEqual(log.actor, self.admin_user)
        set_account_state(self.user, "active", actor=self.admin_user, reason="Appeal accepted")
        self.assertEqual(get_account_state(self.user), "active")
        self.assertTrue(AuditLog.objects.filter(action="account.reinstated").exists())

    def test_reason_is_required_and_state_is_limited(self):
        with self.assertRaises(ValueError):
            set_account_state(self.user, "suspended", actor=self.admin_user, reason="  ")
        with self.assertRaises(ValueError):
            set_account_state(self.user, "deleted", actor=self.admin_user, reason="x")

    def test_setting_the_same_state_writes_no_audit_row(self):
        set_account_state(self.user, "suspended", actor=self.admin_user, reason="a")
        set_account_state(self.user, "suspended", actor=self.admin_user, reason="b")
        self.assertEqual(AuditLog.objects.filter(action="account.suspended").count(), 1)

    def test_suspended_students_are_blocked_but_active_ones_and_anonymous_are_handled(self):
        self.assertEqual(_call(self.user).status_code, 200)
        set_account_state(self.user, "suspended", actor=self.admin_user, reason="test")
        r = _call(self.user)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["code"], "permission_denied")
        self.assertEqual(_call(None).status_code, 401)  # anonymous still gets 401, not 403

    def test_a_suspended_student_can_still_log_in_and_see_their_profile(self):
        set_account_state(self.user, "suspended", actor=self.admin_user, reason="test")
        r = self.client.post("/api/token/", {"username": "stu", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/v1/me").status_code, 200)

    def test_admin_form_suspends_with_a_reason(self):
        self.client.force_login(self.admin_user)
        r = self.client.post(
            "/admin/tps/accounts/accountstatus/add/",
            {"user": self.user.pk, "state": "suspended", "reason": "Repeated reports"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(get_account_state(self.user), "suspended")
        log = AuditLog.objects.get(action="account.suspended")
        self.assertEqual(log.actor, self.admin_user)

    def test_admin_form_refuses_a_missing_reason(self):
        self.client.force_login(self.admin_user)
        r = self.client.post(
            "/admin/tps/accounts/accountstatus/add/", {"user": self.user.pk, "state": "suspended"}
        )
        self.assertEqual(r.status_code, 200)  # form shown again with an error
        self.assertEqual(get_account_state(self.user), "active")


class AnonymiseTests(APITestCase):
    def setUp(self):
        self.sci = Faculty.objects.create(name="Science")
        self.phy = Department.objects.create(name="Physics", faculty=self.sci)
        self.user = User.objects.create_user(
            "ada_obi", "ada@example.com", PASSWORD, first_name="Ada", last_name="Obi"
        )
        self.profile = UserProfile.objects.create(
            user=self.user, faculty=self.sci, department=self.phy,
            phone="08012345678", network="MTN", student_id="S1", matric_number="M1", points=40,
        )
        self.admin_user = User.objects.create_superuser("root", "r@example.com", PASSWORD)
        UserTimetableEntry.objects.create(user=self.user, subject="Maths", day="Monday", time="08:00")
        UserTodoEntry.objects.create(user=self.user, task="Read")
        UserNoteEntry.objects.create(
            user=self.user, note_id="n1", title="T", body="B", color=1, note_updated_at=timezone.now()
        )
        UserGpaEntry.objects.create(user=self.user, course_name="Maths", unit=3, grade="A", grade_point=5)
        UserPreferences.objects.create(user=self.user)
        UserDebaterProgress.objects.create(user=self.user)
        ContactMessage.objects.create(
            user=self.user, name="Ada Obi", email="ada@example.com", subject="Hi", message="Hello"
        )
        self.request = AccountDeletionRequest.objects.create(user=self.user)
        ResetPasswordToken.objects.create(user=self.user)
        self.refresh = str(RefreshToken.for_user(self.user))

    def test_personal_data_is_removed_and_the_account_is_disabled(self):
        self.assertTrue(anonymise_user(self.user, actor=self.admin_user, reason="Deletion request approved"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, f"deleted-{self.user.pk}")
        self.assertEqual((self.user.email, self.user.first_name, self.user.last_name), ("", "", ""))
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.has_usable_password())
        self.profile.refresh_from_db()
        self.assertEqual(
            (self.profile.phone, self.profile.network, self.profile.student_id, self.profile.matric_number),
            ("", "", "", ""),
        )
        for model in (UserTimetableEntry, UserTodoEntry, UserNoteEntry, UserGpaEntry,
                      UserPreferences, UserDebaterProgress, AccountDeletionRequest, ResetPasswordToken):
            self.assertEqual(model.objects.filter(user=self.user).count(), 0, model.__name__)
        message = ContactMessage.objects.get(user=self.user)
        self.assertEqual((message.name, message.email), ("", ""))
        self.assertEqual(get_account_state(self.user), "deleted")

    def test_history_points_and_sessions_are_handled_correctly(self):
        history_before = StudentDepartmentHistory.objects.filter(user=self.user).count()
        anonymise_user(self.user, actor=self.admin_user, reason="test")
        self.assertEqual(StudentDepartmentHistory.objects.filter(user=self.user).count(), history_before)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 40)  # ledger integrity: points are not touched
        self.assertEqual(BlacklistedToken.objects.filter(token__user=self.user).count(), 1)

    def test_the_audit_row_carries_no_personal_data(self):
        anonymise_user(self.user, actor=self.admin_user, reason="Deletion request approved")
        log = AuditLog.objects.get(action="account.anonymised")
        text = f"{log.before}{log.after}{log.reason}"
        self.assertNotIn("ada_obi", text)
        self.assertNotIn("ada@example.com", text)
        self.assertEqual(log.actor, self.admin_user)

    def test_it_is_idempotent(self):
        self.assertTrue(anonymise_user(self.user, actor=self.admin_user, reason="test"))
        self.assertFalse(anonymise_user(self.user, actor=self.admin_user, reason="test"))
        self.assertEqual(AuditLog.objects.filter(action="account.anonymised").count(), 1)

    def test_the_old_login_stops_working(self):
        anonymise_user(self.user, actor=self.admin_user, reason="test")
        r = self.client.post("/api/token/", {"username": "ada_obi", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 401)

    # --- the two legacy endpoints that used to hard-delete ---

    def test_approving_a_deletion_request_anonymises_and_keeps_the_response(self):
        client = APIClient()
        client.force_authenticate(self.admin_user)
        r = client.post(
            f"/api/accounts/deletion-requests/{self.request.pk}/action/", {"action": "approve"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "User account permanently deleted."})
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())  # the row survives
        self.assertEqual(get_account_state(self.user), "deleted")
        self.assertFalse(AccountDeletionRequest.objects.filter(pk=self.request.pk).exists())

    def test_rejecting_a_request_still_just_removes_the_request(self):
        client = APIClient()
        client.force_authenticate(self.admin_user)
        r = client.post(
            f"/api/accounts/deletion-requests/{self.request.pk}/action/", {"action": "reject"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(get_account_state(self.user), "active")
        self.assertTrue(User.objects.get(pk=self.user.pk).is_active)

    def test_the_admin_delete_endpoint_anonymises_and_keeps_its_rules(self):
        client = APIClient()
        client.force_authenticate(self.admin_user)
        self.assertEqual(client.delete(f"/api/accounts/users/{self.user.pk}/").status_code, 204)
        self.assertEqual(get_account_state(self.user), "deleted")
        self.assertEqual(client.delete(f"/api/accounts/users/{self.admin_user.pk}/").status_code, 400)
        client.force_authenticate(User.objects.create_user("plain", "p@example.com", PASSWORD))
        self.assertEqual(client.delete(f"/api/accounts/users/{self.admin_user.pk}/").status_code, 403)

    def test_a_deleted_account_cannot_be_reinstated_in_admin(self):
        anonymise_user(self.user, actor=self.admin_user, reason="test")
        row = AccountStatus.objects.get(user=self.user)
        self.client.force_login(self.admin_user)
        r = self.client.post(
            f"/admin/tps/accounts/accountstatus/{row.pk}/change/", {"state": "active", "reason": "oops"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(get_account_state(self.user), "deleted")


class DataExportTests(APITestCase):
    URL = "/api/v1/me/export"

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.sci = Faculty.objects.create(name="Science")
        self.phy = Department.objects.create(name="Physics", faculty=self.sci)
        self.user = User.objects.create_user("stu", "stu@example.com", PASSWORD)
        UserProfile.objects.create(user=self.user, faculty=self.sci, department=self.phy, phone="0801")
        self.other = User.objects.create_user("other", "o@example.com", PASSWORD)
        UserNoteEntry.objects.create(
            user=self.user, note_id="n1", title="Mine", body="b", color=1, note_updated_at=timezone.now()
        )
        UserNoteEntry.objects.create(
            user=self.other, note_id="n2", title="Theirs", body="b", color=1, note_updated_at=timezone.now()
        )
        UserTimetableEntry.objects.create(user=self.user, subject="Maths", day="Monday", time="08:00")
        AuthEvent.objects.create(kind=AuthEvent.KIND_LOGIN, user=self.user, success=True)

    def test_requires_authentication(self):
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "not_authenticated")

    def test_it_returns_only_the_callers_own_data(self):
        self.client.force_authenticate(self.user)
        r = self.client.get(self.URL)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["account"]["username"], "stu")
        self.assertEqual([n["title"] for n in body["notes"]], ["Mine"])
        self.assertEqual(body["timetable"][0]["subject"], "Maths")
        self.assertEqual(len(body["department_history"]), 1)
        self.assertEqual(len(body["login_events"]), 1)
        self.assertEqual(body["profile"]["department"], "Physics")

    def test_it_never_exposes_the_password_and_is_not_cached(self):
        self.client.force_authenticate(self.user)
        r = self.client.get(self.URL)
        self.assertNotIn("password", r.content.decode().lower())
        self.assertEqual(r["Cache-Control"], "no-store")
        self.assertIn("attachment", r["Content-Disposition"])

    def test_an_export_is_audited(self):
        self.client.force_authenticate(self.user)
        self.client.get(self.URL)
        self.assertTrue(AuditLog.objects.filter(action="account.exported", actor=self.user).exists())