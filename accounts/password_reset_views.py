"""Throttled wrappers around django-rest-passwordreset (F9).

Same URLs and response shapes as the library; the only new response is 429.
Why not per-IP: behind the proxy REMOTE_ADDR is shared by every student, so a
per-IP limit would let one attacker lock everyone out (decision D-10).
"""
import hashlib
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import Throttled
from django_rest_passwordreset import views as lib

from accounts.models import AuthEvent

HOUR = timedelta(hours=1)
REQUESTS_PER_EMAIL_PER_HOUR = 3
REQUESTS_TOTAL_PER_HOUR = 200
CONFIRM_FAILURES_PER_HOUR = 100


def _email_hash(request):
    email = request.data.get("email") if hasattr(request.data, "get") else None
    email = email.strip().lower() if isinstance(email, str) else ""
    return hashlib.sha256(email.encode()).hexdigest() if email else ""


def _ip(request):
    return request.META.get("REMOTE_ADDR") or None


def _recent(kind, **filters):
    since = timezone.now() - HOUR
    return AuthEvent.objects.filter(kind=kind, created_at__gte=since, **filters)


class ResetRequestView(lib.ResetPasswordRequestToken):
    def post(self, request, *args, **kwargs):
        key = _email_hash(request)
        # Every request counts, whatever the outcome, so the limit cannot be dodged.
        too_many_for_email = key and (
            _recent(AuthEvent.KIND_RESET_REQUEST, key_hash=key).count()
            >= REQUESTS_PER_EMAIL_PER_HOUR
        )
        too_many_total = _recent(AuthEvent.KIND_RESET_REQUEST).count() >= REQUESTS_TOTAL_PER_HOUR
        if too_many_for_email or too_many_total:
            raise Throttled(wait=3600)
        AuthEvent.objects.create(
            kind=AuthEvent.KIND_RESET_REQUEST, key_hash=key, ip_address=_ip(request), success=True
        )
        return super().post(request, *args, **kwargs)


class _GuessGuard:
    """Caps FAILED code guesses across all clients combined."""

    def post(self, request, *args, **kwargs):
        failures = _recent(AuthEvent.KIND_RESET_CONFIRM, success=False).count()
        if failures >= CONFIRM_FAILURES_PER_HOUR:
            raise Throttled(wait=3600)
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            # A bad or expired code raises (400/404). Record it, then let the
            # library's own error response go out unchanged.
            AuthEvent.objects.create(
                kind=AuthEvent.KIND_RESET_CONFIRM, ip_address=_ip(request), success=False
            )
            raise
        AuthEvent.objects.create(
            kind=AuthEvent.KIND_RESET_CONFIRM, ip_address=_ip(request), success=True
        )
        return response


class ResetConfirmView(_GuessGuard, lib.ResetPasswordConfirm):
    pass


class ResetValidateView(_GuessGuard, lib.ResetPasswordValidateToken):
    pass