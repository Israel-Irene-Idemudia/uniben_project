from common.views import V1ListAPIView

from .models import XPLedgerEntry
from .serializers import XPEntrySerializer
from .services import get_summary


class MyXPView(V1ListAPIView):
    """GET /api/v1/me/xp  (BE-04, Phase 3 task 3.10)

    Cursor-paginated ledger entries (newest first) plus a `summary` block that
    is repeated on every page, so a client never needs a second call to draw
    the XP header. Read-only: nothing here can award or change XP.
    """

    serializer_class = XPEntrySerializer

    def get_queryset(self):
        # Object-level authorisation: only the caller's own rows, always.
        return XPLedgerEntry.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["summary"] = get_summary(request.user)
        return response
