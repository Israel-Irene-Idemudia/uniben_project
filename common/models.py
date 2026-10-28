from django.conf import settings
from django.db import models


class IdempotencyKey(models.Model):
    """One row per successfully completed idempotent request (API-04).

    CASCADE on the user is deliberate here and is the exception to our
    "never CASCADE" rule: this is a disposable replay cache, not history.
    Ledger and audit rows (which must survive) use PROTECT.

    A committed row always has its response filled in: the row and the
    response are written in the same transaction as the view's own writes.
    The nullable fields exist only for the moment between claiming the key
    and finishing the view.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    endpoint = models.CharField(max_length=255)  # "POST /api/v1/..."
    key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "endpoint", "key"],
                name="uniq_idempotency_user_endpoint_key",
            )
        ]

    def __str__(self):
        return f"{self.endpoint} [{self.key}]"