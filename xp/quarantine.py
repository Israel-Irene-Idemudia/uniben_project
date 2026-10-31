"""Quarantine an XP award (Phase 4.5, BE-05.5). The ONLY write path.

Scope (DECISIONS.md D-22): the minimum for correct leaderboard scoring.
A quarantined award scores on no board until it is cleared. Clearing,
review queues, appeals and anomaly detectors are Phase 5.8 / 6.7.

Rules:
- The actor needs `xp.quarantine_xp_award` (superusers have it). No API
  endpoint exists; the only caller is the admin.
- A reason is mandatory. Every new quarantine writes an AuditLog row in
  the same transaction.
- Only `award` rows can be quarantined: they are the only rows that score
  (D-19). Spends, adjustments and opening balances never reach a board.
- Idempotent: an award already under quarantine returns its open record
  and writes nothing (no second audit row).
- The ledger row is never changed, and the balance, lifetime XP and level
  are NOT affected (D-2 is unchanged). This is a board exclusion only.
"""
from django.db import IntegrityError, transaction

from common.services import log_audit

from .models import XPLedgerEntry, XPQuarantine

QUARANTINE_PERMISSION = "xp.quarantine_xp_award"


class QuarantineError(Exception):
    """An expected refusal (no reason, wrong kind of row)."""


class QuarantinePermissionDenied(QuarantineError):
    """The actor may not quarantine awards."""


def can_quarantine(actor) -> bool:
    return bool(
        actor is not None
        and getattr(actor, "is_active", False)
        and actor.has_perm(QUARANTINE_PERMISSION)
    )


def open_quarantine(entry):
    """The award's open quarantine record, or None."""
    return XPQuarantine.objects.filter(
        entry=entry, state__in=XPQuarantine.EXCLUDING_STATES
    ).first()


def is_quarantined(entry) -> bool:
    return open_quarantine(entry) is not None


def quarantine_award(entry, *, actor, reason, request_id=None):
    """Hold one award off every leaderboard. Returns the open XPQuarantine."""
    if not can_quarantine(actor):
        raise QuarantinePermissionDenied("You do not have permission to quarantine XP awards.")
    reason = (reason or "").strip()
    if not reason:
        raise QuarantineError("A reason is required.")

    with transaction.atomic():
        # Lock the ledger row so two admins queue up (no-op on SQLite).
        entry = XPLedgerEntry.objects.select_for_update().get(pk=entry.pk)
        if entry.kind != XPLedgerEntry.KIND_AWARD:
            raise QuarantineError("Only XP awards can be quarantined.")
        existing = open_quarantine(entry)
        if existing is not None:
            return existing
        try:
            with transaction.atomic():
                record = XPQuarantine.objects.create(
                    entry=entry,
                    state=XPQuarantine.STATE_QUARANTINED,
                    source=XPQuarantine.SOURCE_MANUAL,
                    reason=reason,
                    flagged_by=actor,
                )
        except IntegrityError:
            # Lost a race to another admin: theirs is the open record.
            return open_quarantine(entry)
        log_audit(
            actor=actor,
            action="xp.quarantine",
            target_type="XPLedgerEntry",
            target_id=entry.pk,
            before={"quarantined": False},
            after={
                "quarantined": True,
                "quarantine_id": record.pk,
                "user_id": entry.user_id,
                "amount": entry.amount,
                "reason_code": entry.reason_code,
            },
            reason=reason,
            request_id=request_id,
        )
        return record
