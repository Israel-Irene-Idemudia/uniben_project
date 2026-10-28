import threading
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserTodoEntry
from common.models import IdempotencyKey

URL = "/api/v1/_test/todos/"
URL_B = "/api/v1/_test/todos-b/"
REJECT = "/api/v1/_test/todos-reject/"
EXPLODE = "/api/v1/_test/todos-explode/"


def post(client, url, key, task="a"):
    extra = {} if key is None else {"HTTP_IDEMPOTENCY_KEY": key}
    return client.post(url, {"task": task}, format="json", **extra)


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class IdempotencyTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("idem", password="x-Pass-12345")
        self.client.force_authenticate(self.user)

    def todos(self):
        return UserTodoEntry.objects.count()

    def test_missing_header_is_a_validation_error(self):
        response = post(self.client, URL, None)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("Idempotency-Key", response.data["field_errors"])
        self.assertEqual(self.todos(), 0)

    def test_first_request_runs_and_is_stored(self):
        response = post(self.client, URL, "key-1")
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("Idempotent-Replayed", response)
        self.assertEqual(self.todos(), 1)
        self.assertEqual(IdempotencyKey.objects.count(), 1)

    def test_replay_returns_stored_response_without_running_again(self):
        first = post(self.client, URL, "key-1")
        second = post(self.client, URL, "key-1")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data, first.data)
        self.assertEqual(second["Idempotent-Replayed"], "true")
        self.assertEqual(self.todos(), 1)

    def test_same_key_with_a_different_body_is_a_conflict(self):
        post(self.client, URL, "key-1", task="a")
        response = post(self.client, URL, "key-1", task="different")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "conflict")
        self.assertEqual(self.todos(), 1)

    def test_key_is_scoped_per_user(self):
        other = get_user_model().objects.create_user("idem2", password="x-Pass-12345")
        other_client = APIClient()
        other_client.force_authenticate(other)
        first = post(self.client, URL, "shared-key")
        second = post(other_client, URL, "shared-key")
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(self.todos(), 2)

    def test_key_is_scoped_per_endpoint(self):
        first = post(self.client, URL, "shared-key")
        second = post(self.client, URL_B, "shared-key")
        self.assertEqual((first.status_code, second.status_code), (201, 201))
        self.assertEqual(self.todos(), 2)

    def test_invalid_keys_are_rejected(self):
        for bad in ("bad key", "a" * 129, "x/y"):
            with self.subTest(key=bad):
                response = post(self.client, URL, bad)
                self.assertEqual(response.status_code, 400)
                self.assertIn("Idempotency-Key", response.data["field_errors"])
        self.assertEqual(self.todos(), 0)

    def test_failed_request_releases_the_key_but_keeps_its_effects(self):
        first = post(self.client, REJECT, "key-1")
        self.assertEqual(first.status_code, 400)
        self.assertEqual(IdempotencyKey.objects.count(), 0)
        self.assertEqual(self.todos(), 1)  # the "attempt" row was kept
        second = post(self.client, REJECT, "key-1")
        self.assertEqual(second.status_code, 400)  # ran again, not replayed
        self.assertNotIn("Idempotent-Replayed", second)
        self.assertEqual(self.todos(), 2)

    def test_exception_releases_the_key_and_rolls_back_effects(self):
        with self.assertLogs("common.exceptions", level="ERROR"):
            response = post(self.client, EXPLODE, "key-1")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(IdempotencyKey.objects.count(), 0)
        self.assertEqual(self.todos(), 0)


@skipUnless(
    connection.vendor == "postgresql",
    "Needs PostgreSQL: SQLite cannot prove row locking.",
)
@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class IdempotencyConcurrencyTests(TransactionTestCase):
    def test_parallel_requests_with_one_key_run_once(self):
        user = get_user_model().objects.create_user("racer", password="x-Pass-12345")
        results = []

        def worker():
            try:
                client = APIClient()
                client.force_authenticate(user)
                results.append(post(client, URL, "race-1").status_code)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(UserTodoEntry.objects.filter(user=user).count(), 1)
        self.assertEqual(results, [201] * 5)