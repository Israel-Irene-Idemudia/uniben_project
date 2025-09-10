from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news'
from django.apps import AppConfig

def ready(self):
    import news.signals  # 👈 this makes Django load your signals
