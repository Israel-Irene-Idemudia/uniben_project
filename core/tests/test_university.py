"""Multi-university foundation: core.University and Faculty.university."""
from django.contrib import admin
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import UserProfile
from core.models import Department, Faculty, Level, University

User = get_user_model()


class UniversityModelTests(TestCase):
    def test_uniben_is_seeded_by_migration(self):
        uniben = University.objects.get(code="uniben")
        self.assertEqual(uniben.short_name, "UNIBEN")
        self.assertTrue(uniben.is_active)

    def test_faculty_university_is_optional(self):
        # Additive change: a faculty created without a university still works.
        f = Faculty.objects.create(name="Science")
        self.assertIsNone(f.university)

    def test_university_with_faculties_cannot_be_deleted(self):
        uni = University.objects.create(name="Other", code="other")
        Faculty.objects.create(name="Arts", university=uni)
        with self.assertRaises(ProtectedError):
            uni.delete()

    def test_admin_cannot_delete_universities(self):
        root = User.objects.create_superuser("root", "r@example.com", "x")
        request = RequestFactory().get("/")
        request.user = root
        self.assertFalse(admin.site._registry[University].has_delete_permission(request))


class UniversityApiTests(TestCase):
    def setUp(self):
        self.uniben = University.objects.get(code="uniben")
        self.other = University.objects.create(name="University of Lagos", code="unilag", short_name="UNILAG")
        University.objects.create(name="Closed", code="closed", is_active=False)
        self.sci = Faculty.objects.create(name="Science", university=self.uniben)
        self.law = Faculty.objects.create(name="Law", university=self.other)
        self.phy = Department.objects.create(name="Physics", faculty=self.sci)
        Department.objects.create(name="Private Law", faculty=self.law)

    def test_universities_public_and_active_only(self):
        r = self.client.get("/api/v1/universities")
        self.assertEqual(r.status_code, 200)
        codes = [u["code"] for u in r.json()["results"]]
        self.assertEqual(codes, ["uniben", "unilag"])
        self.assertEqual(set(r.json()["results"][0]), {"id", "name", "code", "short_name"})

    def test_faculties_filter_by_university(self):
        r = self.client.get(f"/api/v1/faculties?university_id={self.other.id}")
        self.assertEqual([f["name"] for f in r.json()["results"]], ["Law"])

    def test_faculties_shape_unchanged_without_filter(self):
        r = self.client.get("/api/v1/faculties")
        self.assertEqual(set(r.json()["results"][0]), {"id", "name", "code"})
        self.assertEqual(len(r.json()["results"]), 2)

    def test_departments_filter_by_university(self):
        r = self.client.get(f"/api/v1/departments?university_id={self.uniben.id}")
        self.assertEqual([d["name"] for d in r.json()["results"]], ["Physics"])

    def test_bad_university_filter_is_validation_error(self):
        r = self.client.get("/api/v1/faculties?university_id=x")
        self.assertEqual(r.status_code, 400)
        self.assertIn("university_id", r.json()["field_errors"])

    def test_me_reports_university_through_faculty(self):
        user = User.objects.create_user("ada", "ada@example.com", "Pass#12345")
        UserProfile.objects.create(
            user=user, faculty=self.sci, department=self.phy,
            level=Level.objects.create(name="100L", department=self.phy),
        )
        client = APIClient()
        client.force_authenticate(user)
        body = client.get("/api/v1/me").json()
        self.assertEqual(body["university"], {"id": self.uniben.id, "name": "University of Benin", "code": "uniben"})

    def test_me_university_is_null_without_faculty(self):
        user = User.objects.create_user("new", "new@example.com", "Pass#12345")
        client = APIClient()
        client.force_authenticate(user)
        self.assertIsNone(client.get("/api/v1/me").json()["university"])
