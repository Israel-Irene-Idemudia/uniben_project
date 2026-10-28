from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import UserTodoEntry


class RowsMixin:
    def make_rows(self, count, same_timestamp=False):
        user = get_user_model().objects.create_user("pager", password="x-Pass-12345")
        self.client.force_authenticate(user)
        rows = [
            UserTodoEntry.objects.create(user=user, task=f"task {i}")
            for i in range(count)
        ]
        # auto_now_add cannot be set on create, so set it afterwards. Distinct
        # timestamps give a clean order; identical ones test the tie-breaker.
        base = timezone.now()
        for i, row in enumerate(rows):
            stamp = base if same_timestamp else base + timedelta(seconds=i)
            UserTodoEntry.objects.filter(pk=row.pk).update(created_at=stamp)
        return rows

    def walk(self, url, page_size):
        """Follow next_cursor to the end; return every id seen, in order."""
        seen = []
        params = {"page_size": page_size}
        for _ in range(20):  # guard: a paging bug must fail, not hang
            response = self.client.get(url, params)
            self.assertEqual(response.status_code, 200, response.data)
            seen += [item["id"] for item in response.data["results"]]
            cursor = response.data["next_cursor"]
            if not cursor:
                return seen
            params = {"page_size": page_size, "cursor": cursor}
        self.fail("Cursor paging did not finish.")


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class CursorPaginationTests(RowsMixin, APITestCase):
    url = "/api/v1/_test/cursor/"

    def test_default_page_size_and_next_cursor(self):
        self.make_rows(25)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next_cursor"])

    def test_walking_cursors_returns_every_row_once_newest_first(self):
        rows = self.make_rows(25)
        seen = self.walk(self.url, page_size=10)
        self.assertEqual(seen, sorted((r.id for r in rows), reverse=True))

    def test_rows_with_identical_timestamps_are_not_skipped_or_repeated(self):
        rows = self.make_rows(25, same_timestamp=True)
        seen = self.walk(self.url, page_size=10)
        self.assertEqual(seen, sorted((r.id for r in rows), reverse=True))

    def test_page_size_is_capped_at_the_maximum(self):
        self.make_rows(25)
        response = self.client.get("/api/v1/_test/cursor-tiny/", {"page_size": 1000})
        self.assertEqual(len(response.data["results"]), 5)

    def test_invalid_cursor_is_a_validation_error(self):
        self.make_rows(1)
        response = self.client.get(self.url, {"cursor": "garbage"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("cursor", response.data["field_errors"])

    def test_empty_list(self):
        self.make_rows(0)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"results": [], "next_cursor": None})


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class PageNumberPaginationTests(RowsMixin, APITestCase):
    url = "/api/v1/_test/pages/"

    def test_first_page_metadata(self):
        rows = self.make_rows(25)
        response = self.client.get(self.url, {"page_size": 10})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["page_size"], 10)
        self.assertEqual(response.data["total_pages"], 3)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [r.id for r in rows[:10]],
        )

    def test_last_page_is_partial(self):
        self.make_rows(25)
        response = self.client.get(self.url, {"page": 3, "page_size": 10})
        self.assertEqual(len(response.data["results"]), 5)

    def test_page_beyond_the_last_is_a_validation_error(self):
        self.make_rows(25)
        response = self.client.get(self.url, {"page": 4, "page_size": 10})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("page", response.data["field_errors"])

    def test_non_numeric_or_non_positive_page_is_a_validation_error(self):
        self.make_rows(5)
        for value in ("abc", "0", "-1"):
            with self.subTest(page=value):
                response = self.client.get(self.url, {"page": value})
                self.assertEqual(response.status_code, 400)
                self.assertIn("page", response.data["field_errors"])


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class ListAuthTests(APITestCase):
    def test_v1_lists_require_authentication(self):
        for path in ("/api/v1/_test/cursor/", "/api/v1/_test/pages/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.data["code"], "not_authenticated")