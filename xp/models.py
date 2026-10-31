"""XP ledger models (BE-04, DATA-04).

NAMING: everything here is "XP..." or "LevelConfig". Never call an XP level
"Level": core.Level already means the academic level (100L, 200L).

DECISION (Phase 4.1, season): the ledger still has NO season column. A row
belongs to a season when its created_at falls in the season's window (see
seasons/models.py for why). Supersedes the Phase 3 plan to add a nullable FK.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from common.models import ImmutableRecordError


class XPLedgerEntryQuerySet(models.QuerySet):
    """No bulk path may rewrite or remove ledger rows (BE-04.1).

    bulk_create stays allowed: appending is what a ledger does. The opening
    balance migration uses historical models, which do not carry this class,
    so its reverse step can still remove its own rows.
    """

    def update(self, **kwargs):
        raise ImmutableRecordError("XP ledger rows cannot be updated.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ImmutableRecordError("XP ledger rows cannot be updated.")

    def delete(self):
        raise ImmutableRecordError("XP ledger rows cannot be deleted.")


class XPLedgerEntry(models.Model):
    """One append-only row per XP movement. Balances are SUMS of these rows.

    Write rows only through xp.services. There is no update or delete path.
    user and created_by are PROTECT (never CASCADE): history must survive, and
    account deletion anonymises instead of deleting (BE-01.6, DATA-17).

    amount is signed: awards are >= 0 (0 means "attempted but capped", see
    services.award_xp), spends are < 0, adjustments are non-zero either way,
    opening balances are > 0. The CHECK constraint enforces that in the DB.
    """

    KIND_AWARD = "award"
    KIND_SPEND = "spend"
    KIND_ADJUSTMENT = "adjustment"
    KIND_OPENING_BALANCE = "opening_balance"
    KIND_CHOICES = [
        (KIND_AWARD, "Award"),
        (KIND_SPEND, "Spend"),
        (KIND_ADJUSTMENT, "Adjustment"),
        (KIND_OPENING_BALANCE, "Opening balance"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="xp_entries"
    )
    amount = models.IntegerField()
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    reason_code = models.CharField(max_length=100)
    source_feature = models.CharField(max_length=50)
    source_record_id = models.CharField(max_length=100, blank=True)
    idempotency_key = models.CharField(max_length=128)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = XPLedgerEntryQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # The real double-award guard (BE-04.3): same user + same key = one row.
            models.UniqueConstraint(
                fields=["user", "idempotency_key"],
                name="uniq_xp_ledger_user_idempotency_key",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="award", amount__gte=0)
                    | Q(kind="spend", amount__lt=0)
                    | (Q(kind="adjustment") & ~Q(amount=0))
                    | Q(kind="opening_balance", amount__gt=0)
                ),
                name="xp_ledger_amount_matches_kind",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "created_at"], name="xp_ledger_user_created_idx"),
            models.Index(
                fields=["user", "reason_code", "created_at"], name="xp_ledger_user_reason_idx"
            ),
        ]

    def __str__(self):
        return f"user {self.user_id}: {self.kind} {self.amount} ({self.reason_code})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ImmutableRecordError("XP ledger rows cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableRecordError("XP ledger rows cannot be deleted.")






class XPAdjustment(XPLedgerEntry):
    """Admin-only view of adjustment rows, used for the 'adjust XP' form
    (BE-04.7). A proxy: no table of its own."""

    class Meta:
        proxy = True
        verbose_name = "XP adjustment"
        verbose_name_plural = "XP adjustments"


class XPRule(models.Model):
    """How much an action earns and how it is limited (BE-04.4, BE-04.5).

    Data, not code: edited in admin, every edit audited, effective for NEW
    awards immediately (season-boundary effective dates need Seasons, Phase 4).
    Caps and diminishing returns use the Africa/Lagos day.

    diminishing_after / diminishing_percent: once a student has earned
    `diminishing_after` awards for this action today, each further award is
    paid at `diminishing_percent`% (never below 1 XP).
    """

    action_code = models.SlugField(max_length=100, unique=True)
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    daily_cap = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max XP per student per day. Empty = no cap."
    )
    diminishing_after = models.PositiveIntegerField(null=True, blank=True)
    diminishing_percent = models.PositiveSmallIntegerField(
        default=50, validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["action_code"]

    def __str__(self):
        return f"{self.action_code} (+{self.amount})"


class LevelConfig(models.Model):
    """One rung of the XP level curve (BE-04.4). Named LevelConfig on purpose.

    A student's level is the highest level whose xp_threshold is <= their
    LIFETIME XP. To change a rung, add a row with a later effective_from.
    """

    level = models.PositiveIntegerField()
    xp_threshold = models.PositiveIntegerField()
    title = models.CharField(max_length=100)
    effective_from = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["level", "effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["level", "effective_from"], name="uniq_level_config_level_from"
            )
        ]

    def __str__(self):
        return f"Level {self.level}: {self.title} (from {self.xp_threshold} XP)"
