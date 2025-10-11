# core/cloudinary_override.py

from cloudinary_storage.storage import MediaCloudinaryStorage
from django.core.files.storage import default_storage

# If Django still points to FileSystemStorage, override it
if not isinstance(default_storage, MediaCloudinaryStorage):
    from django.core.files.storage import storages
    storages._storages.clear()
    from django.conf import settings
    settings.DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    print("🔄 Forced Cloudinary storage override applied")
