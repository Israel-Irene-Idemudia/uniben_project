from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import StudentDepartmentHistory, UserProfile
from core.models import Department, Faculty, Level

User = get_user_model()


class V1MeTests(APITestCase):
    def setUp(self):
        self.sci = Faculty.objects.create(name="Science", code="SCI")
        self.phy = Department.objects.create(name="Physics", faculty=self.sci)
        self.chm = Department.objects.create(name="Chemistry", faculty=self.sci)
        self.level = Level.objects.create(name="100L", department=self.phy)
        self.user = User.objects.create_user("stu", "stu@example.com", "Pass#12345", first_name="Ada", last_name="Obi")
        self.profile = UserProfile.objects.create(
            user=self.user, faculty=self.sci, department=self.phy, level=self.level,
            points=70, phone="08012345678", matric_number="M123",
        )

    def auth(self):
        self.client.force_authenticate(self.user)

    def test_me_requires_authentication_in_v1_shape(self):
        for url in ("/api/v1/me", "/api/v1/me/progress"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 401)
            self.assertEqual(r.json()["code"], "not_authenticated")

    def test_get_me_splits_public_and_private_and_hides_points(self):
        self.auth()
        body = self.client.get("/api/v1/me").json()
        self.assertEqual(body["display_name"], "Ada Obi")
        self.assertEqual(body["department"]["name"], "Physics")
        self.assertEqual(body["academic_level"]["name"], "100L")
        self.assertEqual(body["private"]["matric_number"], "M123")
        self.assertNotIn("matric_number", body)  # private stays inside "private"
        self.assertNotIn("points", body)
        self.assertNotIn("points", body["private"])
        self.assertTrue(body["profile_complete"])
        self.assertEqual(body["badges"], [])

    def test_user_without_profile_gets_complete_your_profile_state(self):
        other = User.objects.create_user("old", "old@example.com", "Pass#12345")
        self.client.force_authenticate(other)
        body = self.client.get("/api/v1/me").json()
        self.assertFalse(body["profile_complete"])
        self.assertEqual(body["missing_fields"], ["faculty", "department", "level"])

    def test_each_student_sees_only_their_own_record(self):
        other = User.objects.create_user("other", "o@example.com", "Pass#12345")
        UserProfile.objects.create(user=other, matric_number="OTHER")
        self.client.force_authenticate(other)
        body = self.client.get("/api/v1/me").json()
        self.assertEqual(body["private"]["matric_number"], "OTHER")

    def test_patch_updates_allowed_fields(self):
        self.auth()
        r = self.client.patch("/api/v1/me", {"phone": "08099999999", "first_name": "Adaeze"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.profile.phone, "08099999999")
        self.assertEqual(self.user.first_name, "Adaeze")

    def test_patch_cannot_change_department_and_points_and_xp(self):
        self.auth()
        for payload in ({"department_id": self.chm.id}, {"points": 999999}, {"xp": 5}):
            r = self.client.patch("/api/v1/me", payload, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["code"], "validation_error")
            self.assertIn(next(iter(payload)), r.json()["field_errors"])
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 70)
        self.assertEqual(self.profile.department_id, self.phy.id)
        self.assertEqual(StudentDepartmentHistory.objects.filter(user=self.user).count(), 1)

    def test_patch_rejects_bad_phone(self):
        self.auth()
        r = self.client.patch("/api/v1/me", {"phone": "call me!"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.json()["field_errors"])

    def test_progress_has_placeholders_until_the_ledger_exists(self):
        self.auth()
        body = self.client.get("/api/v1/me/progress").json()
        self.assertFalse(body["ledger_ready"])
        for key in ("xp_total", "level", "xp_to_next_level", "personal_rank", "department_rank"):
            self.assertIsNone(body[key])
        self.assertEqual(body["department"]["name"], "Physics")
        self.assertEqual(body["suggested_activities"], [])

    def test_trailing_slash_accepted(self):
        self.auth()
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 200)