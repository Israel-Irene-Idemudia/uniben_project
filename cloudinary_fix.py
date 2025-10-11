import os
import django

# Tell Django which settings to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uniben_portal.settings')

django.setup()

from django.conf import settings
from django.core.files.storage import storages
from importlib import import_module

print(f"✅ Cloudinary successfully configured for: {settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', 'Unknown')}")

# --- Force reload Cloudinary Storage ---
storages._storages.clear()

# Dynamically import the Cloudinary storage backend
module_path, class_name = 'cloudinary_storage.storage.MediaCloudinaryStorage'.rsplit('.', 1)
storage_class = getattr(import_module(module_path), class_name)

settings.DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

print(f"✅ Default storage manually switched to: {storage_class}")
