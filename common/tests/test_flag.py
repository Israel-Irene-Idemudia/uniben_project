from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from accounts.models import UserProfile
from common.flags import is_enabled
from common.models import FeatureFlag
from core.models import Department, Faculty

SEEDED = {
    "badges",
    "friends",
    "classrooms",
    "courses_audio",
    "presence",
    "live_location",
    "business_discovery",
}


class IsEnabledTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("flaguser", password="x-Pass-12345")
        faculty = Faculty.objects.create(name="Faculty")
        self.dept = Department.objects.create(name="Dept A", faculty=faculty)
        self.other_dept = Department.objects.create(name="Dept B", faculty=faculty)

    def make_flag(self, **kwargs):
        values = {"name": "test_flag", "enabled": True, "audience": FeatureFlag.AUDIENCE_ALL}
        values.update(kwargs)
        return FeatureFlag.objects.create(**values)

    def set_department(self, department):
        # update_or_create: works whether or not a signal already made a profile.
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"department": department}
        )

    def test_unknown_flag_is_off(self):
        self.assertFalse(is_enabled("does_not_exist", self.user))

    def test_disabled_flag_is_off_even_for_a_cohort_member(self):
        flag = self.make_flag(enabled=False, audience=FeatureFlag.AUDIENCE_COHORT)
        flag.users.add(self.user)
        self.assertFalse(is_enabled("test_flag", self.user))

    def test_all_audience_is_on_for_a_logged_in_user(self):
        self.make_flag()
        self.assertTrue(is_enabled("test_flag", self.user))

    def test_all_audience_is_on_for_anonymous_callers(self):
        self.make_flag()
        self.assertTrue(is_enabled("test_flag"))
        self.assertTrue(is_enabled("test_flag", AnonymousUser()))

    def test_cohort_member_is_on(self):
        flag = self.make_flag(audience=FeatureFlag.AUDIENCE_COHORT)
        flag.users.add(self.user)
        self.assertTrue(is_enabled("test_flag", self.user))

    def test_cohort_non_member_is_off(self):
        self.make_flag(audience=FeatureFlag.AUDIENCE_COHORT)
        self.assertFalse(is_enabled("test_flag", self.user))

    def test_cohort_is_off_for_anonymous_callers(self):
        flag = self.make_flag(audience=FeatureFlag.AUDIENCE_COHORT)
        flag.users.add(self.user)
        self.assertFalse(is_enabled("test_flag"))
        self.assertFalse(is_enabled("test_flag", AnonymousUser()))

    def test_department_member_is_on(self):
        flag = self.make_flag(audience=FeatureFlag.AUDIENCE_DEPARTMENT)
        flag.departments.add(self.dept)
        self.set_department(self.dept)
        self.assertTrue(is_enabled("test_flag", self.user))

    def test_other_department_is_off(self):
        flag = self.make_flag(audience=FeatureFlag.AUDIENCE_DEPARTMENT)
        flag.departments.add(self.dept)
        self.set_department(self.other_dept)
        self.assertFalse(is_enabled("test_flag", self.user))

    def test_user_without_a_profile_is_off(self):
        flag = self.make_flag(audience=FeatureFlag.AUDIENCE_DEPARTMENT)
        flag.departments.add(self.dept)
        UserProfile.objects.filter(user=self.user).delete()
        fresh_user = get_user_model().objects.get(pk=self.user.pk)  # no cached profile
        self.assertFalse(is_enabled("test_flag", fresh_user))

    def test_profile_without_a_department_is_off(self):
        flag = self.make_flag(audience=FeatureFlag.AUDIENCE_DEPARTMENT)
        flag.departments.add(self.dept)
        self.set_department(None)
        self.assertFalse(is_enabled("test_flag", self.user))

    def test_release_2_and_3_flags_are_seeded_and_off(self):
        flags = FeatureFlag.objects.filter(name__in=SEEDED)
        self.assertEqual({flag.name for flag in flags}, SEEDED)
        self.assertFalse(any(flag.enabled for flag in flags))