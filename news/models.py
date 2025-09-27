from django.db import models
from django.conf import settings

    
class News(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    for_all = models.BooleanField(
        default=False,
        help_text="Check this if everyone should see this news (overrides faculty/department/level)."
    )
    faculty = models.ForeignKey("core.Faculty", on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey("core.Department", on_delete=models.CASCADE, null=True, blank=True)
    level = models.ForeignKey("core.Level", on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title

