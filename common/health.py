import logging

from django.db import DatabaseError, connection
from rest_framework.response import Response

from common.exceptions import ServiceUnavailable
from common.views import PublicV1APIView

logger = logging.getLogger(__name__)


class HealthView(PublicV1APIView):
    """Liveness: 200 if the process is up. Never touches the database.

    Not throttled: monitors and load balancers poll this, often from one IP.
    """

    throttle_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class ReadyView(PublicV1APIView):
    """Readiness: 200 only if the database answers; otherwise 503.

    The response never includes the underlying error. The cause goes to the
    log, found through the request ID in the 503 body.
    """

    throttle_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            logger.exception("Readiness check failed: database unavailable")
            raise ServiceUnavailable("Database is unavailable.") from None
        return Response({"status": "ready"})