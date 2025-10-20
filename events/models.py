from django.db import models
from cloudinary_storage.storage import MediaCloudinaryStorage

class Event(models.Model):
    event_date = models.DateTimeField(null=False, blank=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200)
    image = models.ImageField(
        upload_to='events/',
        storage=MediaCloudinaryStorage(),  # ✅ Explicitly use Cloudinary
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
