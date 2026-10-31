"""GET /api/v1/scoring-rules (Phase 4.2, BE-05.6)."""
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AccountStatus, UserProfile
from core.models import Faculty, University
from leaderboards.services import activate_rule_set, create_draft, set_item
from xp.models import XPRule
from xp.tests.helpers import make_admin, make_student

URL = "/api/v1/scoring-rules"


class ScoringRulesApiTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student("stu")
        self.xp_rule = XPRule.objects.create(action_code="test_a", amount=1)
        self.uni = University.objects.create(name="Test Uni", code="testuni")
        self.other = University.objects.create(name="Other Uni", code="otheruni")
        profile = UserProfile.objects.get(user=self.student)
        profile.faculty = Faculty.objects.create(name="Science", university=self.uni)
        profile.save()
        self.client = APIClient()
        self.client.force_authenticate(self.student)

    def publish(self, university=None, name="Rule", weight="1.50", activate=True):
        rs = create_draft(
            name=name, university=university, summary="Exactly how it works.", student_cap=200,
            actor=self.admin, reason="r",
        )
        set_item(rs, xp_rule=self.xp_rule, label="Practice", weight=weight, per_student_cap=50, actor=self.admin, reason="r")
        return activate_rule_set(rs, actor=self.admin, reason="r") if activate else rs

    def test_requires_authentication(self):
        r = APIClient().get(URL)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "not_authenticated")

    def test_null_when_nothing_is_published(self):
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"rule_set": None})

    def test_drafts_are_never_published(self):
        self.publish(activate=False)
        self.publish(university=self.uni, activate=False, name="Uni draft")
        self.assertIsNone(self.client.get(URL).json()["rule_set"])

    def test_returns_the_rule_verbatim(self):
        rs = self.publish()
        body = self.client.get(URL + "/").json()["rule_set"]
        self.assertEqual(
            set(body),
            {"id", "name", "scope", "university", "summary", "student_cap", "uncapped", "activated_at", "activities"},
        )
        self.assertEqual((body["id"], body["scope"], body["university"]), (rs.id, "global", None))
        self.assertEqual(body["summary"], "Exactly how it works.")
        self.assertEqual((body["student_cap"], body["uncapped"]), (200, False))
        self.assertEqual(
            body["activities"],
            [{"action_code": "test_a", "label": "Practice", "weight": "1.50", "per_student_cap": 50}],
        )

    def test_callers_own_university_rule_wins_over_global(self):
        self.publish(name="Global")
        own = self.publish(university=self.uni, name="Own")
        body = self.client.get(URL).json()["rule_set"]
        self.assertEqual(body["id"], own.id)
        self.assertEqual(body["scope"], "university")
        self.assertEqual(body["university"], {"id": self.uni.id, "name": "Test Uni", "code": "testuni"})

    def test_explicit_university_and_global_fallback(self):
        global_rule = self.publish(name="Global")
        self.publish(university=self.uni, name="Own")
        body = self.client.get(f"{URL}?university_id={self.other.id}").json()["rule_set"]
        self.assertEqual(body["id"], global_rule.id)

    def test_student_without_profile_gets_global_and_no_profile_is_created(self):
        global_rule = self.publish(name="Global")
        loner = make_student("loner")
        UserProfile.objects.filter(user=loner).delete()
        client = APIClient()
        client.force_authenticate(loner)
        self.assertEqual(client.get(URL).json()["rule_set"]["id"], global_rule.id)
        self.assertFalse(UserProfile.objects.filter(user=loner).exists())

    def test_bad_and_unknown_university_ids(self):
        r = self.client.get(f"{URL}?university_id=abc")
        self.assertEqual(r.status_code, 400)
        self.assertIn("university_id", r.json()["field_errors"])
        r = self.client.get(f"{URL}?university_id=999999")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["code"], "not_found")

    def test_read_only(self):
        self.assertEqual(self.client.post(URL, {}, format="json").status_code, 405)

    def test_suspended_students_can_still_read_the_rules(self):
        self.publish()
        AccountStatus.objects.create(user=self.student, state=AccountStatus.SUSPENDED)
        self.assertEqual(self.client.get(URL).status_code, 200)
