from django.contrib import admin
from django.test import RequestFactory, TestCase
from django.contrib.auth import get_user_model

from core.models import Department, Faculty

User = get_user_model()


class RegistryFieldsTests(TestCase):
    def test_new_fields_default_safely(self):
        f = Faculty.objects.create(name="Science")
        d = Department.objects.create(name="Physics", faculty=f)
        self.assertTrue(f.is_active)
        self.assertIsNone(f.code)
        self.assertTrue(d.is_active)
        self.assertIsNone(d.code)

    def test_duplicate_codes_are_allowed_for_now(self):
        Faculty.objects.create(name="A", code="SCI")
        Faculty.objects.create(name="B", code="SCI")  # no unique constraint until 2.1 is clean

    def test_admin_cannot_delete_registry_rows(self):
        admin_user = User.objects.create_superuser("root", "r@example.com", "x")
        request = RequestFactory().get("/")
        request.user = admin_user
        for model in (Faculty, Department):
            self.assertFalse(admin.site._registry[model].has_delete_permission(request))


class RegistryV1ApiTests(TestCase):
    def setUp(self):
        self.sci = Faculty.objects.create(name="Science", code="SCI")
        self.eng = Faculty.objects.create(name="Engineering")
        self.old = Faculty.objects.create(name="Retired", is_active=False)
        self.phy = Department.objects.create(name="Physics", faculty=self.sci)
        self.chm = Department.objects.create(name="Chemistry", faculty=self.sci)
        self.mech = Department.objects.create(name="Mechanical", faculty=self.eng)
        Department.objects.create(name="Closed", faculty=self.sci, is_active=False)
        Department.objects.create(name="Orphan", faculty=self.old)

    def test_faculties_public_and_active_only(self):
        r = self.client.get("/api/v1/faculties")
        self.assertEqual(r.status_code, 200)
        names = [x["name"] for x in r.json()["results"]]
        self.assertEqual(names, ["Engineering", "Science"])
        self.assertEqual(set(r.json()["results"][0]), {"id", "name", "code"})

    def test_departments_hide_inactive_rows(self):
        r = self.client.get("/api/v1/departments")
        names = [x["name"] for x in r.json()["results"]]
        self.assertEqual(names, ["Chemistry", "Mechanical", "Physics"])

    def test_departments_filter_by_faculty(self):
        r = self.client.get(f"/api/v1/departments?faculty_id={self.sci.id}")
        names = [x["name"] for x in r.json()["results"]]
        self.assertEqual(names, ["Chemistry", "Physics"])
        self.assertEqual(r.json()["results"][0]["faculty_id"], self.sci.id)

    def test_bad_filter_uses_v1_error_shape(self):
        r = self.client.get("/api/v1/departments?faculty_id=abc")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "validation_error")
        self.assertIn("faculty_id", r.json()["field_errors"])
        self.assertTrue(r.json()["request_id"])

    def test_bad_token_does_not_break_public_list(self):
        self.client.credentials = None
        r = self.client.get("/api/v1/faculties", HTTP_AUTHORIZATION="Bearer junk")
        self.assertEqual(r.status_code, 200)

    def test_trailing_slash_accepted(self):
        self.assertEqual(self.client.get("/api/v1/faculties/").status_code, 200)

    def test_legacy_endpoints_unchanged(self):
        r = self.client.get("/api/core/faculties/")
        self.assertEqual(r.status_code, 200)
        rows = r.json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        self.assertEqual(set(rows[0]), {"id", "name"})
        # legacy still lists retired rows: it is untouched by design
        self.assertEqual(len(rows), 3)