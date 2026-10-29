"""Login lockout and the auth log (BE-01.4, decision D-15).

Counted in the database (AuthEvent), so it works across gunicorn workers.
Keyed per ACCOUNT, not per IP: behind the proxy every student shares one IP
(decision D-10), so a per-IP limit would lock everybody out at once.
Trade-off, accepted for now: someone who knows a student's email can keep
that one account locked for up to an hour, but still cannot guess the password.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta
from math import ceil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import AuthEvent
from common.services import get_setting

logger = logging.getLogger(__name__)
User = get_user_model()

DEFAULT_THRESHOLD = 5
DEFAULT_SCHEDULE_MINUTES = [1, 5, 15, 60]
LOOKBACK = timedelta(hours=24)  # a quiet day forgives old failures
RETENTION = timedelta(days=90)  # DATA-17
BAD_CREDENTIALS = "bad_credentials"
LOCKED = "locked"


def lockout_threshold():
    value = get_setting("auth.lockout_threshold", DEFAULT_THRESHOLD)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return DEFAULT_THRESHOLD
    return min(value, 50)


def lockout_schedule():
    value = get_setting("auth.lockout_schedule_minutes", DEFAULT_SCHEDULE_MINUTES)
    if (
        isinstance(value, list)
        and value
        and all(isinstance(m, int) and not isinstance(m, bool) and 0 < m <= 1440 for m in value)
    ):
        return value
    return DEFAULT_SCHEDULE_MINUTES


def login_key(identifier):
    """Returns (key, user_or_None) for whatever the student typed.

    Email and username of the same account share one key, so switching
    between them does not reset the count. A name that does not exist gets a
    key too, so it locks exactly like a real one (nothing about whether an
    account exists leaks). The key is an HMAC, never the name itself.
    """
    identifier = identifier.strip()
    user = User.objects.filter(email=identifier).first() or User.objects.filter(
        username=identifier
    ).first()
    ident = f"user:{user.pk}" if user else f"name:{identifier.lower()}"
    digest = hmac.new(settings.SECRET_KEY.encode(), ident.encode(), hashlib.sha256).hexdigest()
    return digest, user


def _failures(key):
    """(count, time of the latest) of failures since the last success.
    Attempts rejected while locked are not failures, so they cannot extend a lock."""
    since = timezone.now() - LOOKBACK
    base = AuthEvent.objects.filter(kind=AuthEvent.KIND_LOGIN, key_hash=key, created_at__gte=since)
    last_ok = (
        base.filter(success=True).order_by("-created_at").values_list("created_at", flat=True).first()
    )
    fails = base.filter(success=False).exclude(detail=LOCKED)
    if last_ok is not None:
        fails = fails.filter(created_at__gt=last_ok)
    return fails.count(), fails.order_by("-created_at").values_list("created_at", flat=True).first()


def failure_count(key):
    return _failures(key)[0]


def lock_seconds_remaining(key):
    """0 if the account may try now, else seconds until it may."""
    failures, last = _failures(key)
    threshold = lockout_threshold()
    if failures < threshold or last is None:
        return 0
    schedule = lockout_schedule()
    minutes = schedule[min((failures - threshold) // 2, len(schedule) - 1)]
    remaining = (last + timedelta(minutes=minutes) - timezone.now()).total_seconds()
    return max(0, ceil(remaining))


def lock_message(seconds):
    minutes = max(1, ceil(seconds / 60))
    return f"Too many failed attempts. Try again in {minutes} minute(s)."


def _ip(request):
    return request.META.get("REMOTE_ADDR") or None


def record_login_event(request, key, user, *, success, detail=""):
    """Write one auth-log row. Never lets a logging problem break a login."""
    try:
        AuthEvent.objects.create(
            kind=AuthEvent.KIND_LOGIN,
            key_hash=key,
            user=user,
            ip_address=_ip(request),
            success=success,
            detail=detail,
        )
        if secrets.randbelow(50) == 0:  # no scheduler yet (D-5): tidy up as we go
            purge_old_events()
    except Exception:
        logger.exception("Could not record a login event")


def purge_old_events(batch=500):
    """Delete up to `batch` auth-log rows older than 90 days. Returns how many."""
    cutoff = timezone.now() - RETENTION
    ids = list(AuthEvent.objects.filter(created_at__lt=cutoff).values_list("pk", flat=True)[:batch])
    if not ids:
        return 0
    AuthEvent.objects.filter(pk__in=ids).delete()
    return len(ids)