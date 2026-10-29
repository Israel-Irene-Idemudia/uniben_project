from datetime import timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import DepartmentChangeApproval
from accounts.models import StudentDepartmentHistory as History
from accounts.models import UserProfile
from common.models import AuditLog
from common.services import set_setting
from core.models import Department, Faculty, Level

User = get_user_model()
URL = "/api/v1/me/department-change"
LAGOS = ZoneInfo("Africa/Lagos")


class DepartmentChangeTests(APITestCase):
    def setUp(self):
        self.sci = Faculty.objects.create(name="Science")
        self.eng = Faculty.objects.create(name="Engineering")
        self.phy = Department.objects.create(name="Physics", faculty=self.sci)
        self.chm = Department.objects.create(name="Chemistry", faculty=self.sci)
        self.mech = Department.objects.create(name="Mechanical", faculty=self.eng)
        self.closed = Department.objects.create(name="Closed", faculty=self.sci, is_active=False)
        self.lvl_phy = Level.objects.create(name="100L", department=self.phy)
        self.lvl_chm = Level.objects.create(name="100L", department=self.chm)
        self.user = User.objects.create_user("stu", "stu@example.com", "Pass#12345")
        self.profile = UserProfile.objects.create(
            user=self.user, faculty=self.sci, department=self.phy, level=self.lvl_phy
        )
        self.admin_user = User.objects.create_superuser("root", "r@example.com", "Pass#12345")
        self.client.force_authenticate(self.user)

    def _change(self, department, **extra):
        return self.client.post(URL, {"department_id": department.id, **extra}, format="json")

    def _age_changes(self, days):
        History.objects.filter(user=self.user, reason="Department change").update(
            effective_from=timezone.now() - timedelta(days=days)
        )

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        r = self.client.post(URL, {"department_id": self.chm.id}, format="json")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "not_authenticated")

    def test_change_moves_student_and_writes_history_and_audit(self):
        r = self._change(self.chm, reason="Switched course")
        self.assertEqual(r.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.department_id, self.chm.id)
        self.assertEqual(self.profile.faculty_id, self.sci.id)
        rows = {h.department_name: h for h in History.objects.filter(user=self.user)}
        self.assertEqual(set(rows), {"Physics", "Chemistry"})  # exactly one new row
        self.assertIsNotNone(rows["Physics"].effective_to)  # past kept, closed
        self.assertIsNone(rows["Chemistry"].effective_to)
        log = AuditLog.objects.get(action="department.change")
        self.assertEqual(log.before["department_id"], self.phy.id)
        self.assertEqual(log.after["department_id"], self.chm.id)
        self.assertEqual(log.reason, "Switched course")

    def test_level_is_cleared_unless_it_belongs_to_the_new_department(self):
        body = self._change(self.chm).json()
        self.assertFalse(body["profile_complete"])
        self.assertEqual(body["missing_fields"], ["level"])

    def test_level_of_the_new_department_is_kept(self):
        r = self._change(self.chm, level_id=self.lvl_chm.id)
        self.assertEqual(r.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.level_id, self.lvl_chm.id)

    def test_level_of_another_department_is_rejected(self):
        r = self._change(self.chm, level_id=self.lvl_phy.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn("level_id", r.json()["field_errors"])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.department_id, self.phy.id)

    def test_cross_faculty_change_updates_faculty(self):
        self._change(self.mech)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.faculty_id, self.eng.id)

    def test_same_department_is_a_field_error(self):
        r = self._change(self.phy)
        self.assertEqual(r.status_code, 400)
        self.assertIn("department_id", r.json()["field_errors"])

    def test_inactive_or_unknown_department_is_rejected(self):
        for dept_id in (self.closed.id, 999999):
            r = self.client.post(URL, {"department_id": dept_id}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertIn("department_id", r.json()["field_errors"])

    def test_second_change_in_the_same_semester_is_blocked(self):
        self.assertEqual(self._change(self.chm).status_code, 200)
        r = self._change(self.mech)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["code"], "conflict")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.department_id, self.chm.id)
        self.assertEqual(History.objects.filter(user=self.user).count(), 2)

    def test_fallback_window_is_180_days(self):
        self._change(self.chm)
        self._age_changes(179)
        self.assertEqual(self._change(self.mech).status_code, 409)
        self._age_changes(181)
        self.assertEqual(self._change(self.mech).status_code, 200)

    def test_semester_settings_define_the_window(self):
        today = timezone.now().astimezone(LAGOS).date()
        set_setting("academic.semester_start", (today - timedelta(days=30)).isoformat(),
                    actor=self.admin_user, reason="test")
        set_setting("academic.semester_end", (today + timedelta(days=30)).isoformat(),
                    actor=self.admin_user, reason="test")
        self._change(self.chm)
        # A change made BEFORE this semester started no longer counts,
        # even though the 180-day fallback would still block it.
        self._age_changes(31)
        self.assertEqual(self._change(self.mech).status_code, 200)

    def test_invalid_settings_fall_back_safely(self):
        set_setting("academic.semester_start", "garbage", actor=self.admin_user, reason="test")
        set_setting("academic.semester_end", "garbage", actor=self.admin_user, reason="test")
        self._change(self.chm)
        self._age_changes(31)
        self.assertEqual(self._change(self.mech).status_code, 409)

    def test_admin_approval_allows_exactly_one_extra_change(self):
        self._change(self.chm)
        approval = DepartmentChangeApproval.objects.create(
            user=self.user, approved_by=self.admin_user, reason="Wrong course at registration"
        )
        self.assertEqual(self._change(self.mech).status_code, 200)
        approval.refresh_from_db()
        self.assertIsNotNone(approval.used_at)
        self.assertEqual(self._change(self.phy).status_code, 409)

    def test_a_student_with_no_department_can_choose_freely(self):
        other = User.objects.create_user("new", "new@example.com", "Pass#12345")
        UserProfile.objects.create(user=other)
        self.client.force_authenticate(other)
        r = self._change(self.chm)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(History.objects.filter(user=other).count(), 1)

    def test_a_student_cannot_change_someone_elses_department(self):
        r = self.client.post(URL, {"department_id": self.chm.id, "user_id": 1}, format="json")
        self.assertEqual(r.status_code, 200)  # extra keys are ignored: only the caller changes
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.department_id, self.chm.id)