from rest_framework.response import Response

from common.views import V1APIView

from .models import Season
from .serializers import SeasonSerializer
from .services import current_season


def _data(season):
    return SeasonSerializer(season).data if season is not None else None


class CurrentSeasonView(V1APIView):
    """GET /api/v1/seasons/current

    The open week and the open term (either may be null). Read-only and
    authenticated (V1APIView). Not IsNotSuspended: knowing the season dates
    is not a competitive action.
    """

    def get(self, request):
        return Response(
            {
                "week": _data(current_season(Season.KIND_WEEK)),
                "term": _data(current_season(Season.KIND_TERM)),
            }
        )
