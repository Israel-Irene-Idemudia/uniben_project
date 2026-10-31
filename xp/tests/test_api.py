from django.test import TestCase
from rest_framework.test import APIClient

from .helpers import make_student


class MyXPEndpointTests(TestCase):
    def setUp(self):
        self.user = make_student("alice", points=120)
        self.other = make_student("bob", points=999)
        self.client = APIClient()

    def test_requires_login(self):
        self.assertIn(self.client.get("/api/v1/me/xp").status_code, (401, 403))

    def test_returns_only_my_entries_with_a_summary(self):
        self.client.force_authenticate(self.user)
        res = self.client.get("/api/v1/me/xp")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["amount"], 120)
        self.assertEqual(res.data["summary"]["balance"], 120)
        self.assertEqual(res.data["summary"]["level"], 2)
        entry = res.data["results"][0]
        self.assertNotIn("idempotency_key", entry)
        self.assertNotIn("metadata", entry)

    def test_trailing_slash_also_works(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/v1/me/xp/").status_code, 200)

    def test_endpoint_is_read_only(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post("/api/v1/me/xp", {"amount": 9999}, format="json").status_code, 405)
