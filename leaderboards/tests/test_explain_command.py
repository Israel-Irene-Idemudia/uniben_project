"""explain_leaderboard prints a plan for the endpoint's own SQL (D-5)."""
import io

from django.core.management import call_command
from django.test import TestCase

from .board_helpers import make_world


class ExplainCommandTests(TestCase):
    def test_prints_a_plan_for_the_endpoint_query(self):
        w = make_world()
        out = io.StringIO()
        call_command("explain_leaderboard", "university", "lifetime", "--unit-id", str(w["u1"].pk), stdout=out)
        text = out.getvalue()
        self.assertIn("-- database: sqlite", text)
        self.assertGreater(len(text.splitlines()), 1)
