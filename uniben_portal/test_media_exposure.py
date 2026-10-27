from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class MediaRouteDoesNotExposeSourceTests(SimpleTestCase):
    """
    SECURITY: with MEDIA_ROOT unset, Django defaults it to "" (the working
    directory), so the /media/ route served project source files.
    """

    def test_source_files_are_not_served(self):
        for path in (
            "/media/uniben_portal/urls.py",
            "/media/uniben_portal/settings.py",
            "/media/manage.py",
            "/media/.env.example",
            "/media/Dockerfile",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_media_root_is_a_dedicated_folder(self):
        self.assertEqual(Path(settings.MEDIA_ROOT), Path(settings.BASE_DIR) / "media")