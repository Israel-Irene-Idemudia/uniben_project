from django.db import models
from django.conf import settings
from cloudinary_storage.storage import MediaCloudinaryStorage

class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(
        upload_to='news_images/',
        storage=MediaCloudinaryStorage(),
        blank=True,
        null=True,
        help_text="Optional image for the news."
    )

    for_all = models.BooleanField(default=False)
    faculty = models.ForeignKey("core.Faculty", on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey("core.Department", on_delete=models.CASCADE, null=True, blank=True)
    level = models.ForeignKey("core.Level", on_delete=models.CASCADE, null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
