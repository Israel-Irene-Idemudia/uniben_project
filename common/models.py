from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator


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


SETTING_KEY_PATTERN = r"[a-z0-9_.]{1,100}"


class PlatformSetting(models.Model):
    """Central configuration, editable in admin without a deploy (BE-20.1).

    Never write this model directly: use common.services.set_setting so the
    change and its audit row are written together.
    """

    key = models.CharField(
        max_length=100,
        unique=True,
        validators=[
            RegexValidator(
                rf"^{SETTING_KEY_PATTERN}$",
                "Use lowercase letters, digits, underscores and dots.",
            )
        ],
    )
    value = models.JSONField()
    description = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,  # the audit log keeps the history
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


class ImmutableRecordError(Exception):
    """Raised on any attempt to change or delete an append-only record."""


class AuditLogQuerySet(models.QuerySet):
    """No bulk path may rewrite or remove audit rows (BE-15.4)."""

    def update(self, **kwargs):
        raise ImmutableRecordError("Audit log rows cannot be updated.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ImmutableRecordError("Audit log rows cannot be updated.")

    def delete(self):
        raise ImmutableRecordError("Audit log rows cannot be deleted.")


class AuditLog(models.Model):
    """Append-only record of admin, moderator and system actions (BE-15.4).

    Write rows only through common.services.log_audit. There is no update or
    delete path in application code. The actor FK is PROTECT (history must
    survive) and actor_label keeps a readable username snapshot.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    actor_label = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=255)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.target_type}:{self.target_id}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ImmutableRecordError("Audit log rows cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableRecordError("Audit log rows cannot be deleted.")