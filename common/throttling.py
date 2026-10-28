"""Rate limits for /api/v1/ (API-07).

Rates live HERE, not in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], and these
classes are attached per view through V1ViewMixin. Nothing global changes, so
legacy endpoints stay unthrottled exactly as before.

Scopes:
- v1_default      every v1 view unless it picks another scope
- v1_auth         login / OTP / reset endpoints (stricter; Phase 2)
- v1_competitive  Past Questions competitive endpoints (stricter; Phase 5)

Known limits (documented, not hidden):
- Counters live in Django's cache. No CACHES setting exists, so that is
  per-process memory: each gunicorn worker counts separately and a restart
  resets the counts. A shared limit needs Redis (decision D-5).
- Anonymous callers are keyed by DRF's get_ident(), which trusts the
  X-Forwarded-For header unless REST_FRAMEWORK["NUM_PROXIES"] is set. Until
  the proxy chain is known (D-10), anonymous limits can be dodged by faking
  that header. Per-user limits for logged-in students are not affected.
- DRF checks throttles AFTER authentication and permissions, so unauthenticated
  calls to a protected endpoint are rejected (401) before they are counted.
"""
from rest_framework.throttling import SimpleRateThrottle


class V1RateThrottle(SimpleRateThrottle):
    THROTTLE_RATES = {
        "v1_default": "120/min",
        "v1_auth": "10/min",
        "v1_competitive": "30/min",
    }

    def get_cache_key(self, request, view):
        user = request.user
        if user is not None and user.is_authenticated:
            ident = user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class V1DefaultThrottle(V1RateThrottle):
    scope = "v1_default"


class V1AuthThrottle(V1RateThrottle):
    scope = "v1_auth"


class V1CompetitiveThrottle(V1RateThrottle):
    scope = "v1_competitive"