"""The only place a Season is created or changes state (BE-20.2).

Every action is audited with a mandatory reason. State moves one way only:
scheduled -> open -> closed. A closed season is never reopened, because its
archived boards (Phase 4.6) must stay final.

Locking: each transition locks the season row, and opening also locks every
open season of the same kind, so two admins cannot open two weeks at once.
The partial unique constraint on (kind, state=open) is the last line of
defence. (Row locks are no-ops on SQLite; effective on PostgreSQL.)
"""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from common.services import log_audit

from .models import Season

LAGOS = ZoneInfo("Africa/Lagos")


class SeasonError(Exception):
    """An expected, user-facing refusal (bad dates, wrong state)."""


def _reason(reason: str) -> str:
    reason = (reason or "").strip()
    if not reason:
        raise SeasonError("A reason is required.")
    return reason


def _aware(value: datetime) -> datetime:
    # A naive datetime is read as Lagos wall-clock time, never as UTC.
    if timezone.is_naive(value):
        return value.replace(tzinfo=LAGOS)
    return value


def _snapshot(season: Season) -> dict:
    return {
        "name": season.name,
        "kind": season.kind,
        "state": season.state,
        "starts_at": season.starts_at.isoformat(),
        "ends_at": season.ends_at.isoformat(),
    }


def _overlapping(kind: str, starts_at: datetime, ends_at: datetime, exclude_pk=None):
    qs = Season.objects.filter(kind=kind, starts_at__lt=ends_at, ends_at__gt=starts_at)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def validate_window(kind: str, starts_at: datetime, ends_at: datetime, exclude_pk=None) -> None:
    """Seasons of one kind never overlap: an XP row must belong to at most
    one week and one term, or boards would double count."""
    if kind not in dict(Season.KIND_CHOICES):
        raise SeasonError("Unknown season kind.")
    if ends_at <= starts_at:
        raise SeasonError("The season must end after it starts.")
    if _overlapping(kind, starts_at, ends_at, exclude_pk).exists():
        raise SeasonError(f"This overlaps another {kind} season.")


def create_season(*, name: str, kind: str, starts_at: datetime, ends_at: datetime, actor, reason: str) -> Season:
    reason = _reason(reason)
    name = (name or "").strip()
    if not name:
        raise SeasonError("A name is required.")
    starts_at, ends_at = _aware(starts_at), _aware(ends_at)
    with transaction.atomic():
        validate_window(kind, starts_at, ends_at)
        season = Season.objects.create(name=name, kind=kind, starts_at=starts_at, ends_at=ends_at)
        log_audit(
            actor=actor, action="season.create", target_type="Season", target_id=season.pk,
            before=None, after=_snapshot(season), reason=reason,
        )
    return season


def reschedule_season(season: Season, *, name: str, starts_at: datetime, ends_at: datetime, actor, reason: str) -> Season:
    """Only a scheduled season may change its name or dates."""
    reason = _reason(reason)
    starts_at, ends_at = _aware(starts_at), _aware(ends_at)
    with transaction.atomic():
        season = Season.objects.select_for_update().get(pk=season.pk)
        if season.state != Season.STATE_SCHEDULED:
            raise SeasonError("Only a scheduled season can be changed.")
        validate_window(season.kind, starts_at, ends_at, exclude_pk=season.pk)
        before = _snapshot(season)
        season.name = (name or season.name).strip()
        season.starts_at, season.ends_at = starts_at, ends_at
        season.save(update_fields=["name", "starts_at", "ends_at"])
        log_audit(
            actor=actor, action="season.update", target_type="Season", target_id=season.pk,
            before=before, after=_snapshot(season), reason=reason,
        )
    return season


def open_season(season: Season, *, actor, reason: str) -> Season:
    reason = _reason(reason)
    with transaction.atomic():
        season = Season.objects.select_for_update().get(pk=season.pk)
        if season.state != Season.STATE_SCHEDULED:
            raise SeasonError(f"A {season.state} season cannot be opened.")
        if Season.objects.select_for_update().filter(kind=season.kind, state=Season.STATE_OPEN).exists():
            raise SeasonError(f"Another {season.kind} season is already open. Close it first.")
        before = _snapshot(season)
        season.state = Season.STATE_OPEN
        season.opened_at = timezone.now()
        season.save(update_fields=["state", "opened_at"])
        log_audit(
            actor=actor, action="season.open", target_type="Season", target_id=season.pk,
            before=before, after=_snapshot(season), reason=reason,
        )
    return season


def close_season(season: Season, *, actor, reason: str) -> Season:
    """Close an open season. Phase 4.6 hooks the board archive in here."""
    reason = _reason(reason)
    with transaction.atomic():
        season = Season.objects.select_for_update().get(pk=season.pk)
        if season.state != Season.STATE_OPEN:
            raise SeasonError(f"A {season.state} season cannot be closed.")
        before = _snapshot(season)
        season.state = Season.STATE_CLOSED
        season.closed_at = timezone.now()
        season.save(update_fields=["state", "closed_at"])
        log_audit(
            actor=actor, action="season.close", target_type="Season", target_id=season.pk,
            before=before, after=_snapshot(season), reason=reason,
        )
    return season


def current_season(kind: str) -> Optional[Season]:
    """The open season of this kind, or None. State, not the clock, decides:
    an admin opens and closes seasons explicitly (BE-20.2)."""
    return Season.objects.filter(kind=kind, state=Season.STATE_OPEN).first()
