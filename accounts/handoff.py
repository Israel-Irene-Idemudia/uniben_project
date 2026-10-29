"""World hand-off keys (BE-01.3, D-8): create one, exchange one."""
import hashlib
import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import WorldHandoffToken
from common.services import get_setting, log_audit

DEFAULT_TTL_SECONDS = 60
MIN_TTL_SECONDS = 10
MAX_TTL_SECONDS = 300
PURGE_AFTER = timedelta(days=1)


class HandoffError(Exception):
    """The key is unknown, used, expired, or its owner is not allowed in.

    One error for every case on purpose: the caller must not be able to tell
    which one it was.
    """


def _hash(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def handoff_ttl_seconds():
    """Lifetime from the admin setting auth.handoff_ttl_seconds, kept between
    10 and 300 seconds. Anything unusable falls back to 60."""
    value = get_setting("auth.handoff_ttl_seconds", DEFAULT_TTL_SECONDS)
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_TTL_SECONDS
    return max(MIN_TTL_SECONDS, min(MAX_TTL_SECONDS, value))


def create_handoff_token(user):
    """Returns (raw_key, lifetime_seconds). The raw key is shown once."""
    now = timezone.now()
    # Housekeeping: remove keys that expired more than a day ago.
    WorldHandoffToken.objects.filter(expires_at__lt=now - PURGE_AFTER).delete()

    raw = secrets.token_urlsafe(32)  # 256 bits: cannot be guessed
    ttl = handoff_ttl_seconds()
    WorldHandoffToken.objects.create(
        user=user, token_hash=_hash(raw), expires_at=now + timedelta(seconds=ttl)
    )
    log_audit(
        actor=user,
        action="auth.handoff_created",
        target_type="User",
        target_id=user.pk,
        after={"expires_in": ttl},
        reason="World hand-off requested",
    )
    return raw, ttl


def exchange_handoff_token(raw):
    """Swap a valid key for a normal session. Returns (user, access, refresh)."""
    now = timezone.now()
    row = WorldHandoffToken.objects.select_related("user").filter(token_hash=_hash(raw)).first()
    if row is None:
        raise HandoffError()

    # One atomic UPDATE claims the key: if two requests arrive together, only
    # one of them can change a row that still has used_at empty.
    claimed = WorldHandoffToken.objects.filter(
        pk=row.pk, used_at__isnull=True, expires_at__gt=now
    ).update(used_at=now)
    if claimed != 1:
        raise HandoffError()

    user = row.user
    if not user.is_active:
        raise HandoffError()

    refresh = RefreshToken.for_user(user)
    log_audit(
        actor=user,
        action="auth.handoff_exchanged",
        target_type="User",
        target_id=user.pk,
        reason="World hand-off exchanged for a session",
    )
    return user, str(refresh.access_token), str(refresh)