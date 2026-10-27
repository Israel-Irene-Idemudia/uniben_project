from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Shared v1 plumbing: error shape, pagination, idempotency, flags, audit.

    Named `common` on purpose: `platform` would shadow the Python standard
    library module of the same name.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
    verbose_name = "Platform"