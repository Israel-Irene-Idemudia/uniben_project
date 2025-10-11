import os
import django

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uniben_portal.settings")
django.setup()

from django.core.files.storage import default_storage
from django.conf import settings

print("=====================================")
print("Settings DEFAULT_FILE_STORAGE:", settings.DEFAULT_FILE_STORAGE)
print("Actual default_storage class:", default_storage.__class__)
print("=====================================")
