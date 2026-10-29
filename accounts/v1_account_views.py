from rest_framework.response import Response

from accounts.data_export import export_user_data
from common.services import log_audit
from common.throttling import V1AuthThrottle
from common.views import V1APIView


class MeExportView(V1APIView):
    """The student's own data as JSON (BE-01.6). Strict rate limit: it is a big query."""

    throttle_classes = [V1AuthThrottle]

    def get(self, request):
        data = export_user_data(request.user)
        log_audit(
            actor=request.user,
            action="account.exported",
            target_type="User",
            target_id=request.user.pk,
            reason="Student downloaded their own data",
        )
        response = Response(data)
        response["Cache-Control"] = "no-store"
        response["Content-Disposition"] = 'attachment; filename="skholar-my-data.json"'
        return response