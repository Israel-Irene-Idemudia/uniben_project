"""Seasons (Phase 4.1, BE-20.2).

A season is a time window that week and season leaderboards are computed
over. Lifetime boards ignore seasons.

DECISION (season membership of XP): the ledger gets NO season FK. An XP row
belongs to a season when its created_at falls inside [starts_at, ends_at).
Why: the ledger is append-only, so a season stamped at write time could never
be corrected if an admin fixes a season's dates later; a time window can.
The (user, created_at) ledger index already serves these range queries.
Revisit only if a board needs awards that belong to a season they were not
earned in.

Boundaries are chosen in Africa/Lagos and stored in UTC (USE_TZ). Lagos has
no daylight saving, so a week season is always exactly 7 * 24 hours.
"""
from django.db import models
from django.db.models import F, Q


class Season(models.Model):
    KIND_WEEK = "week"
    KIND_TERM = "term"
    KIND_CHOICES = [(KIND_WEEK, "Week"), (KIND_TERM, "Term")]

    STATE_SCHEDULED = "scheduled"
    STATE_OPEN = "open"
    STATE_CLOSED = "closed"
    STATE_CHOICES = [
        (STATE_SCHEDULED, "Scheduled"),
        (STATE_OPEN, "Open"),
        (STATE_CLOSED, "Closed"),
    ]

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    starts_at = models.DateTimeField(help_text="Stored in UTC. Pick the Lagos time you want.")
    ends_at = models.DateTimeField(help_text="Exclusive end. Stored in UTC.")
    # Written only by seasons.services; read-only in admin.
    state = models.CharField(max_length=10, choices=STATE_CHOICES, default=STATE_SCHEDULED)
    opened_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-starts_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")),
                name="season_ends_after_start",
            ),
            # At most one open season of each kind: "the current week" and
            # "the current term" must each be unambiguous.
            models.UniqueConstraint(
                fields=["kind"],
                condition=Q(state="open"),
                name="uniq_open_season_per_kind",
            ),
        ]
        indexes = [models.Index(fields=["kind", "state"], name="season_kind_state_idx")]

    def __str__(self):
        return f"{self.name} ({self.kind}, {self.state})"
