from django.apps import AppConfig
from django.core.files.storage import default_storage
from cloudinary_storage.storage import MediaCloudinaryStorage
from django.conf import settings
import cloudinary
import cloudinary.uploader
import cloudinary.api


class MaterialsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'materials'

    def ready(self):
        import sys
        if 'test' in sys.argv or any('test' in arg for arg in sys.argv):
            return

        # Force Django to use Cloudinary storage for all media uploads
        settings.DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

        # Manually override the already-loaded default storage
        from django.core.files.storage import default_storage
        if not isinstance(default_storage, MediaCloudinaryStorage):
            print("Replacing FileSystemStorage with MediaCloudinaryStorage...")
            from django.core.files.storage import Storage
            from django.core.files.storage import storages
            storages._storages["default"] = MediaCloudinaryStorage()

