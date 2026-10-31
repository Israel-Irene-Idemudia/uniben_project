"""The ONLY place XP is written (BE-04, decision D7: the server is authoritative).

Rules every function here follows:
- One transaction. The student's auth row is locked (SELECT ... FOR UPDATE)
  before anything is read, so two requests for the same student queue up and
  cannot double-spend or beat a cap together. (A no-op on SQLite, effective on
  PostgreSQL: the concurrency tests only prove it on PostgreSQL.)
- Idempotent by (user, idempotency_key). The same key again returns the
  existing row and writes nothing. The same key with a DIFFERENT request is a
  conflict, never a silent second award.
- Nothing trusts a client number. Amounts come from XPRule rows or from
  server-validated records (a quest's own reward), never from request bodies.

DECISION D-2 (two numbers from one ledger):
- lifetime XP = award + adjustment + opening_balance rows. Drives level and
  (later) leaderboards. Spending never lowers it, so a level never drops
  because a student bought airtime.
- spendable balance = ALL rows, spends included. This is what the old
  `points` meant, and what the Flutter app still shows.

DECISION (profile mirror): UserProfile.points is no longer a source of truth.
But the live Flutter app still reads it (login payload, profile serializer),
so after every ledger write we copy the spendable balance into it. It is a
write-only cache: written HERE and nowhere else, never read to make a
decision. Remove it, and this mirror, after the Release 1 gate.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from common.services import log_audit

from .models import LevelConfig, XPLedgerEntry, XPRule

logger = logging.getLogger(__name__)

# Daily boundaries use Lagos local time; timestamps are stored in UTC.
# Lagos has no daylight saving, so a day is always exactly 24 hours.
LAGOS = ZoneInfo("Africa/Lagos")

LIFETIME_KINDS = (
    XPLedgerEntry.KIND_AWARD,
    XPLedgerEntry.KIND_ADJUSTMENT,
    XPLedgerEntry.KIND_OPENING_BALANCE,
)


class XPError(Exception):
    """Base class for expected, catchable ledger problems."""


class UnknownXPAction(XPError):
    """No active XPRule exists for this action code."""


class InsufficientPoints(XPError):
    def __init__(self, balance, cost):
        super().__init__(f"Insufficient points: have {balance}, need {cost}.")
        self.balance = balance
        self.cost = cost


class IdempotencyConflict(XPError):
    """The key was already used for a different request."""


class AdjustmentRefused(XPError):
    """An admin adjustment would push a student below zero."""


@dataclass(frozen=True)
class AwardResult:
    entry: XPLedgerEntry
    created: bool  # False = this was a replay of an earlier event
    capped: bool  # True = nothing was paid (daily cap reached)


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    lifetime_xp: int
    xp_to_next_level: Optional[int]  # None at the top level


def lagos_day_bounds(now=None):
    """(start, end) of the Lagos calendar day containing `now`, as aware datetimes."""
    local = (now or timezone.now()).astimezone(LAGOS)
    start = datetime.combine(local.date(), time.min, tzinfo=LAGOS)
    return start, start + timedelta(days=1)


def _lock_user(user):
    # Lock the auth user row (every student has one), not UserProfile, which
    # some accounts may lack.
    return get_user_model().objects.select_for_update().get(pk=user.pk)


def _total(user, kinds=None):
    qs = XPLedgerEntry.objects.filter(user=user)
    if kinds is not None:
        qs = qs.filter(kind__in=kinds)
    return qs.aggregate(total=Sum("amount"))["total"] or 0


def get_balance(user):
    """Spendable balance: every ledger row, spends included."""
    return _total(user)


def get_lifetime_xp(user):
    """Lifetime XP: awards, adjustments and opening balance. Spends excluded."""
    return _total(user, LIFETIME_KINDS)


def _sync_profile_mirror(user, balance):
    # See the module docstring: a write-only cache for the live Flutter app.
    from accounts.models import UserProfile

    UserProfile.objects.filter(user_id=user.pk).update(points=balance)


def _existing(user, key):
    return XPLedgerEntry.objects.filter(user=user, idempotency_key=key).first()


def _check_key(key):
    if not key or len(key) > 128:
        raise ValueError("idempotency_key must be 1 to 128 characters.")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def award_xp(
    user,
    *,
    action_code,
    source_feature,
    source_record_id="",
    idempotency_key=None,
    amount=None,
    created_by=None,
    metadata=None,
):
    """Award XP for a server-validated event. Returns an AwardResult.

    `amount` may only be passed by server code that already validated the
    source record (for example a quest's own reward). It is still subject to
    the rule's cap and diminishing returns, and the rule must exist and be
    active, so an admin can switch an action off.

    A capped award still writes a ZERO-amount row. That is deliberate: the row
    holds the idempotency key, so replaying the same event on a later day
    cannot pay out, and the cap hit is visible in the ledger.
    """
    source_record_id = str(source_record_id or "")
    key = idempotency_key or f"{action_code}:{source_feature}:{source_record_id}"
    if not idempotency_key and not source_record_id:
        raise ValueError("Give an idempotency_key or a source_record_id.")
    _check_key(key)
    if amount is not None and (not _is_int(amount) or amount <= 0):
        raise ValueError("amount must be a positive integer.")

    with transaction.atomic():
        _lock_user(user)

        existing = _existing(user, key)
        if existing is not None:
            if (
                existing.kind != XPLedgerEntry.KIND_AWARD
                or existing.reason_code != action_code
                or existing.source_feature != source_feature
                or existing.source_record_id != source_record_id
            ):
                raise IdempotencyConflict("This key was already used for a different award.")
            return AwardResult(existing, created=False, capped=existing.amount == 0)

        rule = XPRule.objects.filter(action_code=action_code, is_active=True).first()
        if rule is None:
            raise UnknownXPAction(f"No active XP rule for '{action_code}'.")

        base = rule.amount if amount is None else amount
        final = base
        meta = dict(metadata or {})
        meta["base_amount"] = base

        start, end = lagos_day_bounds()
        today = XPLedgerEntry.objects.filter(
            user=user,
            kind=XPLedgerEntry.KIND_AWARD,
            reason_code=action_code,
            amount__gt=0,
            created_at__gte=start,
            created_at__lt=end,
        ).aggregate(total=Sum("amount"), n=Count("id"))
        earned_today = today["total"] or 0
        awards_today = today["n"] or 0

        if rule.diminishing_after is not None and awards_today >= rule.diminishing_after:
            final = max(1, base * rule.diminishing_percent // 100)
            meta["diminished"] = True

        if rule.daily_cap is not None:
            room = rule.daily_cap - earned_today
            if room <= 0:
                final = 0
                meta["capped"] = True
            elif final > room:
                final = room
                meta["capped"] = "partial"

        # No IntegrityError handling: the row lock above queues same-student
        # requests, and the unique constraint stays as the last line of defence.
        entry = XPLedgerEntry.objects.create(
            user=user,
            amount=final,
            kind=XPLedgerEntry.KIND_AWARD,
            reason_code=action_code,
            source_feature=source_feature,
            source_record_id=source_record_id,
            idempotency_key=key,
            created_by=created_by,
            metadata=meta,
        )
        if final > 0:
            _sync_profile_mirror(user, get_balance(user))
        return AwardResult(entry, created=True, capped=final == 0)


def spend_points(
    user,
    *,
    cost,
    reason_code,
    source_feature,
    source_record_id="",
    idempotency_key,
    created_by=None,
    metadata=None,
):
    """Spend points (for example a reward). Returns the ledger row.

    Raises InsufficientPoints if the spendable balance is too low. The balance
    is read AFTER taking the row lock, so concurrent spends cannot both pass.
    """
    if not _is_int(cost) or cost <= 0:
        raise ValueError("cost must be a positive integer.")
    _check_key(idempotency_key)
    source_record_id = str(source_record_id or "")

    with transaction.atomic():
        _lock_user(user)

        existing = _existing(user, idempotency_key)
        if existing is not None:
            if (
                existing.kind != XPLedgerEntry.KIND_SPEND
                or existing.reason_code != reason_code
                or existing.source_feature != source_feature
                or existing.source_record_id != source_record_id
                or existing.amount != -cost
            ):
                raise IdempotencyConflict("This key was already used for a different spend.")
            return existing

        balance = get_balance(user)
        if balance < cost:
            raise InsufficientPoints(balance, cost)

        entry = XPLedgerEntry.objects.create(
            user=user,
            amount=-cost,
            kind=XPLedgerEntry.KIND_SPEND,
            reason_code=reason_code,
            source_feature=source_feature,
            source_record_id=source_record_id,
            idempotency_key=idempotency_key,
            created_by=created_by,
            metadata=dict(metadata or {}),
        )
        _sync_profile_mirror(user, balance - cost)
        return entry


def check_adjustment(user, amount):
    """Raise AdjustmentRefused if `amount` would push lifetime XP or the
    balance below zero. Used by the admin form and again inside adjust_xp."""
    if not _is_int(amount) or amount == 0:
        raise AdjustmentRefused("Amount must be a non-zero whole number.")
    if get_lifetime_xp(user) + amount < 0 or get_balance(user) + amount < 0:
        raise AdjustmentRefused("This would take the student below zero.")


def adjust_xp(user, *, amount, reason, actor, idempotency_key):
    """Admin award (+) or deduction (-) with a mandatory reason (BE-04.7).

    Writes the ledger row and an AuditLog row in ONE transaction. Direct
    edits of balances are impossible: the field is a mirror and read-only.
    """
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("A reason is required.")
    if actor is None:
        raise ValueError("An acting admin is required.")
    _check_key(idempotency_key)

    with transaction.atomic():
        _lock_user(user)

        existing = _existing(user, idempotency_key)
        if existing is not None:
            if existing.kind != XPLedgerEntry.KIND_ADJUSTMENT or existing.amount != amount:
                raise IdempotencyConflict("This key was already used for a different adjustment.")
            return existing

        check_adjustment(user, amount)
        before = {"lifetime_xp": get_lifetime_xp(user), "balance": get_balance(user)}

        entry = XPLedgerEntry.objects.create(
            user=user,
            amount=amount,
            kind=XPLedgerEntry.KIND_ADJUSTMENT,
            reason_code="admin_adjustment",
            source_feature="admin",
            source_record_id="",
            idempotency_key=idempotency_key,
            created_by=actor,
            metadata={"reason": reason},
        )
        after = {"lifetime_xp": before["lifetime_xp"] + amount, "balance": before["balance"] + amount}
        _sync_profile_mirror(user, after["balance"])
        log_audit(
            actor=actor,
            action="xp.adjustment",
            target_type="XPLedgerEntry",
            target_id=entry.pk,
            before=before,
            after={**after, "user_id": user.pk, "amount": amount},
            reason=reason,
        )
        return entry


def _effective_levels(now=None):
    """The level curve in force now: for each level, its latest row that has
    already taken effect."""
    now = now or timezone.now()
    by_level = {}
    for cfg in LevelConfig.objects.filter(effective_from__lte=now).order_by("effective_from", "id"):
        by_level[cfg.level] = cfg
    return sorted(by_level.values(), key=lambda c: c.level)


def get_level(user):
    """Level from LIFETIME XP (never from the spendable balance, see D-2)."""
    xp = max(0, get_lifetime_xp(user))
    levels = _effective_levels()
    current = None
    next_threshold = None
    for cfg in levels:
        if cfg.xp_threshold <= xp:
            current = cfg
        elif next_threshold is None:
            next_threshold = cfg.xp_threshold
    if current is None:
        return LevelInfo(
            level=0,
            title="",
            lifetime_xp=xp,
            xp_to_next_level=None if next_threshold is None else next_threshold - xp,
        )
    to_next = None if next_threshold is None else next_threshold - xp
    return LevelInfo(level=current.level, title=current.title, lifetime_xp=xp, xp_to_next_level=to_next)


def get_summary(user):
    """Everything a client needs to draw a student's XP header, in one dict."""
    info = get_level(user)
    return {
        "lifetime_xp": info.lifetime_xp,
        "balance": get_balance(user),
        "level": info.level,
        "level_title": info.title,
        "xp_to_next_level": info.xp_to_next_level,
    }
