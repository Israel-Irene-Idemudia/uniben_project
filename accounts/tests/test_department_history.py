import importlib

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from accounts.models import StudentDepartmentHistory as History
from accounts.models import UserProfile
from core.models import Department, Faculty

User = get_user_model()


class DepartmentHistoryTests(TestCase):
    def setUp(self):
        self.sci = Faculty.objects.create(name="Science")
        self.phy = Department.objects.create(name="Physics", faculty=self.sci)
        self.chm = Department.objects.create(name="Chemistry", faculty=self.sci)
        self.user = User.objects.create_user("stu", "stu@example.com", "Pass#12345")

    def _profile(self, department):
        return UserProfile.objects.create(
            user=self.user, department=department, faculty=department.faculty if department else None
        )

    def test_new_profile_gets_one_open_row_with_name_snapshots(self):
        self._profile(self.phy)
        row = History.objects.get(user=self.user)
        self.assertIsNone(row.effective_to)
        self.assertEqual((row.department_name, row.faculty_name), ("Physics", "Science"))

    def test_change_closes_old_row_and_opens_new_one(self):
        profile = self._profile(self.phy)
        profile.department = self.chm
        profile.save()
        rows = {r.department_name: r for r in History.objects.filter(user=self.user)}
        self.assertIsNotNone(rows["Physics"].effective_to)  # past is kept
        self.assertIsNone(rows["Chemistry"].effective_to)
        self.assertEqual(History.objects.filter(user=self.user, effective_to__isnull=True).count(), 1)

    def test_saving_without_a_change_adds_nothing(self):
        profile = self._profile(self.phy)
        profile.points = 5
        profile.save()
        self.assertEqual(History.objects.filter(user=self.user).count(), 1)

    def test_profile_without_department_has_no_row_until_one_is_set(self):
        profile = self._profile(None)
        self.assertEqual(History.objects.filter(user=self.user).count(), 0)
        profile.department = self.phy
        profile.save()
        self.assertEqual(History.objects.filter(user=self.user).count(), 1)

    def test_clearing_department_closes_the_open_row(self):
        profile = self._profile(self.phy)
        profile.department = None
        profile.save()
        self.assertEqual(History.objects.filter(user=self.user, effective_to__isnull=True).count(), 0)

    def test_rename_does_not_change_the_past(self):
        self._profile(self.phy)
        self.phy.name = "Applied Physics"
        self.phy.save()
        self.assertEqual(History.objects.get(user=self.user).department_name, "Physics")

    def test_only_one_open_row_per_student(self):
        self._profile(self.phy)
        with self.assertRaises(IntegrityError), transaction.atomic():
            History.objects.create(
                user=self.user, department=self.chm, effective_from=self.user.date_joined
            )

    def test_user_with_history_cannot_be_hard_deleted(self):
        # Deliberate (history must survive). Task 2.9 replaces hard deletes
        # with anonymisation.
        self._profile(self.phy)
        with self.assertRaises(ProtectedError):
            self.user.delete()


class BackfillTests(TestCase):
    def setUp(self):
        self.backfill = importlib.import_module(
            "accounts.migrations.0012_backfill_department_history"
        ).backfill
        sci = Faculty.objects.create(name="Science")
        self.phy = Department.objects.create(name="Physics", faculty=sci)
        self.a = User.objects.create_user("a", "a@example.com", "Pass#12345")
        self.b = User.objects.create_user("b", "b@example.com", "Pass#12345")
        UserProfile.objects.create(user=self.a, department=self.phy, faculty=sci)
        UserProfile.objects.create(user=self.b)  # no department
        History.objects.all().delete()  # simulate the state before this phase

    def test_backfill_creates_one_open_row_per_profile_with_a_department(self):
        self.backfill(django_apps, None)
        row = History.objects.get()
        self.assertEqual(row.user, self.a)
        self.assertIsNone(row.effective_to)
        self.assertEqual(row.effective_from, self.a.date_joined)

    def test_backfill_is_safe_to_run_twice(self):
        self.backfill(django_apps, None)
        self.backfill(django_apps, None)
        self.assertEqual(History.objects.count(), 1)