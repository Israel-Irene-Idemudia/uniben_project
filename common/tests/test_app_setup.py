from django.apps import apps
from django.test import SimpleTestCase


class CommonAppSetupTests(SimpleTestCase):
    def test_common_app_is_installed(self):
        self.assertTrue(apps.is_installed("common"))

    def test_common_app_label_does_not_clash_with_stdlib(self):
        config = apps.get_app_config("common")
        self.assertEqual(config.name, "common")