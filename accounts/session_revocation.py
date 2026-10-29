"""Sign a student out everywhere (BE-01.2)."""
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from accounts.models import WorldHandoffToken
from common.services import log_audit


def revoke_all_sessions(user, *, actor=None, reason):
    """Blacklist every outstanding refresh token of `user` and burn their
    unused hand-off keys. Returns how many refresh tokens were revoked.

    Safe to call twice. Access tokens (15 minutes) cannot be recalled; they
    simply expire.
    """
    ids = list(
        OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True).values_list(
            "pk", flat=True
        )
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token_id=pk) for pk in ids], ignore_conflicts=True
    )
    WorldHandoffToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    log_audit(
        actor=actor,
        action="auth.sessions_revoked",
        target_type="User",
        target_id=user.pk,
        after={"revoked_refresh_tokens": len(ids)},
        reason=reason,
    )
    return len(ids)