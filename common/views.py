"""Base classes every /api/v1/ view must use.

Why this exists: the project-wide DRF default permission is
IsAuthenticatedOrReadOnly, so a v1 view that forgets to set permissions would
be publicly readable. We cannot change that global default (it would break the
live legacy endpoints), so v1 views opt in to a safe default through these
classes, and a test fails if a v1 route uses anything else.
"""
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView


class V1ViewMixin:
    """Marks a view as part of v1 and makes it authenticated by default.

    Mix into any DRF view or viewset base (APIView, GenericAPIView, ...).
    Put it first in the bases so these attributes win.
    """

    permission_classes = [IsAuthenticated]


class V1APIView(V1ViewMixin, APIView):
    """Default base for v1 endpoints: JWT-authenticated, no public access."""


class PublicV1APIView(V1ViewMixin, APIView):
    """Base for v1 endpoints that are explicitly public (e.g. health).

    Authentication is switched off entirely so a stale or malformed token in
    the Authorization header cannot turn a public call into a 401.
    Using this class is the explicit "this endpoint is public" marker.
    """

    permission_classes = [AllowAny]
    authentication_classes = []