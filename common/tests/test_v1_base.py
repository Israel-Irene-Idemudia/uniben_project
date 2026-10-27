from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import URLResolver, resolve
from rest_framework.test import APITestCase

from common import v1_urls
from common.views import V1ViewMixin


@override_settings(ROOT_URLCONF="common.tests.v1_test_urls")
class V1DefaultAuthTests(APITestCase):
    protected = "/api/v1/_test/protected/"
    public = "/api/v1/_test/public/"

    def test_protected_requires_authentication(self):
        self.assertEqual(self.client.get(self.protected).status_code, 401)

    def test_protected_allows_authenticated_user(self):
        user = get_user_model().objects.create_user("v1user", password="x-Pass-12345")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.protected).status_code, 200)

    def test_protected_rejects_garbage_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(self.client.get(self.protected).status_code, 401)

    def test_public_allows_anonymous(self):
        self.assertEqual(self.client.get(self.public).status_code, 200)

    def test_public_ignores_garbage_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(self.client.get(self.public).status_code, 200)


class V1WiringTests(SimpleTestCase):
    def test_legacy_routes_still_resolve(self):
        # Compatibility guard (D-11): v1 wiring must not disturb legacy routes.
        for path in (
            "/api/token/",
            "/api/rewards/redeem/",
            "/api/core/faculties/",
            "/api/accounts/register/",
        ):
            with self.subTest(path=path):
                resolve(path)

    def test_v1_is_mounted_before_legacy_api_includes(self):
        # Order matters: legacy "api/" includes must never get first chance
        # at an /api/v1/ path.
        from uniben_portal import urls as root

        prefixes = [str(p.pattern) for p in root.urlpatterns]
        self.assertIn("api/v1/", prefixes)
        self.assertLess(prefixes.index("api/v1/"), prefixes.index("api/"))

    def test_every_v1_route_uses_the_v1_base(self):
        # Safety net for the IsAuthenticatedOrReadOnly global default:
        # a v1 view that skips the base would be publicly readable.
        def callbacks(patterns):
            for p in patterns:
                if isinstance(p, URLResolver):
                    yield from callbacks(p.url_patterns)
                else:
                    yield p

        for p in callbacks(v1_urls.urlpatterns):
            view_class = getattr(p.callback, "view_class", None) or getattr(
                p.callback, "cls", None
            )
            with self.subTest(route=str(p.pattern)):
                self.assertIsNotNone(view_class)
                self.assertTrue(issubclass(view_class, V1ViewMixin))