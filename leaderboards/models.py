"""Contribution rules (Phase 4.2, BE-05.2, BE-05.6).

A rule set says which activities count towards department and faculty
collective boards, at what weight, and with what per-student cap. It is
published to both clients verbatim by GET /api/v1/scoring-rules.

DECISION (D-18, defaults pending Israel's approval):
- Nothing is seeded. The build does not choose which activities count, their
  weights or caps: an admin enters them, and nothing affects any board until
  a rule set is explicitly ACTIVATED by someone with the activate permission.
- An "activity" is an existing XPRule (its action_code is the ledger's
  reason_code), so contributions come from the ledger, never from a client.
- Caps are in contribution points (after the weight). A rule set must either
  set a per-student cap or be marked "uncapped" on purpose; an empty cap is
  never silently read as "no cap".
- Multi-university (D-16): optional university. Resolution is "the
  university's own active set, else the global one", which supports both a
  shared rule and per-university rules without choosing between them.

Lifecycle: draft -> active -> retired, one way. Active and retired sets are
frozen (archived boards must stay explainable); to change the rule, copy it
to a new draft and activate that. Lifecycle changes go through services.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from common.models import ImmutableRecordError

# The only fields services may write on a non-draft rule set.
LIFECYCLE_FIELDS = frozenset({"state", "activated_at", "activated_by", "retired_at", "updated_at"})



class ContributionRuleSet(models.Model):
    STATE_DRAFT = "draft"
    STATE_ACTIVE = "active"
    STATE_RETIRED = "retired"
    STATE_CHOICES = [
        (STATE_DRAFT, "Draft"),
        (STATE_ACTIVE, "Active"),
        (STATE_RETIRED, "Retired"),
    ]

    name = models.CharField(max_length=100)
    university = models.ForeignKey(
        "core.University",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contribution_rule_sets",
        help_text="Empty = applies to every university that has no active rule set of its own.",
    )
    summary = models.TextField(
        blank=True, help_text="Student-facing explanation. Both apps show it exactly as written."
    )
    student_cap = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Most contribution points one student can add per board period.",
    )
    uncapped = models.BooleanField(
        default=False, help_text="Tick only to publish with no per-student cap on purpose."
    )
    # Written only by leaderboards.services; read-only in admin.
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default=STATE_DRAFT)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    retired_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # One active set per university, plus one active global set. Two
            # partial constraints because NULLs never collide in a plain one.
            models.UniqueConstraint(
                fields=["university"],
                condition=Q(state="active", university__isnull=False),
                name="uniq_active_rule_set_per_university",
            ),
            models.UniqueConstraint(
                fields=["state"],
                condition=Q(state="active", university__isnull=True),
                name="uniq_active_global_rule_set",
            ),
            models.CheckConstraint(
                condition=Q(uncapped=False) | Q(student_cap__isnull=True),
                name="rule_set_cap_or_uncapped",
            ),
        ]
        permissions = [
            ("activate_contributionruleset", "Can activate or retire contribution rule sets"),
        ]

    def __str__(self):
        scope = self.university or "all universities"
        return f"{self.name} ({scope}, {self.state})"

    def save(self, *args, **kwargs):
        # Frozen once published. Services may still move the lifecycle fields.
        if not self._state.adding:
            stored = type(self).objects.filter(pk=self.pk).values_list("state", flat=True).first()
            if stored is not None and stored != self.STATE_DRAFT:
                fields = kwargs.get("update_fields")
                if fields is None or not set(fields) <= LIFECYCLE_FIELDS:
                    raise ImmutableRecordError(
                        "A published contribution rule set cannot be edited. Copy it to a new draft."
                    )
        super().save(*args, **kwargs)


class ContributionRuleItem(models.Model):
    """One contributing activity in a rule set."""

    rule_set = models.ForeignKey(ContributionRuleSet, on_delete=models.CASCADE, related_name="items")
    xp_rule = models.ForeignKey("xp.XPRule", on_delete=models.PROTECT, related_name="contribution_items")
    label = models.CharField(max_length=100, blank=True, help_text="Student-facing name of the activity.")
    # Nullable so an unfinished draft can be saved; activation refuses an
    # item without a weight.
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Contribution points per 1 XP earned from this activity.",
    )
    per_student_cap = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Optional: most contribution points one student can add from this activity.",
    )

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["rule_set", "xp_rule"], name="uniq_rule_item_per_action"),
            models.CheckConstraint(
                condition=Q(weight__isnull=True) | Q(weight__gt=0),
                name="rule_item_weight_positive",
            ),
        ]

    def __str__(self):
        return f"{self.label or self.xp_rule_id} x{self.weight}"

    def _rule_set_is_draft(self) -> bool:
        return ContributionRuleSet.objects.filter(
            pk=self.rule_set_id, state=ContributionRuleSet.STATE_DRAFT
        ).exists()

    def save(self, *args, **kwargs):
        if not self._rule_set_is_draft():
            raise ImmutableRecordError("Activities of a published rule set cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self._rule_set_is_draft():
            raise ImmutableRecordError("Activities of a published rule set cannot be removed.")
        return super().delete(*args, **kwargs)
