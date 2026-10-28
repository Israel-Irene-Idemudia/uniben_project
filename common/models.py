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

class FeatureFlag(models.Model):
    """Admin-editable switch for a feature (SRS section 3.3, rule 7).

    Release 2 and 3 features ship dark: every one is seeded OFF and only
    turned on by a person in admin, per cohort or department if wanted.
    """

    AUDIENCE_ALL = "all"
    AUDIENCE_COHORT = "cohort"
    AUDIENCE_DEPARTMENT = "department"
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, "Everyone"),
        (AUDIENCE_COHORT, "Named users (cohort)"),
        (AUDIENCE_DEPARTMENT, "Named departments"),
    ]

    name = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    enabled = models.BooleanField(default=False)
    audience = models.CharField(
        max_length=20, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="feature_flags"
    )
    departments = models.ManyToManyField(
        "core.Department", blank=True, related_name="feature_flags"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({'on' if self.enabled else 'off'}, {self.audience})"