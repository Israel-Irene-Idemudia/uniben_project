"""v1 rewards endpoints (Phase 3, tasks 3.5 and 3.6). Contracts: docs/design/xp-ledger.md."""
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from common.idempotency import idempotent
from common.pagination import V1CursorPagination
from common.views import V1APIView, V1ListAPIView
from xp.services import InsufficientPoints

from .models import Redemption, RewardCatalog
from .serializers import RedemptionSerializer
from .services import ProfileMissing, UnknownReward, redeem_reward
from .views import RedeemInputSerializer


class V1RedeemView(V1APIView):
    """POST /api/v1/rewards/redeem  (requires the Idempotency-Key header)."""

    @idempotent
    def post(self, request):
        serializer = RedeemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            redemption = redeem_reward(
                request.user,
                reward_type=data["reward_type"],
                phone=data["phone"],
                network=data["network"],
                # The ledger gets its own key derived from the header, so even
                # if the HTTP layer were bypassed the spend could not repeat.
                idempotency_key=f"redeem:{request.headers['Idempotency-Key']}",
            )
        except UnknownReward:
            raise ValidationError({"reward_type": ["This reward is not available."]})
        except InsufficientPoints as exc:
            raise ValidationError({"points": [f"Insufficient points: you have {exc.balance}, this costs {exc.cost}."]})
        except ProfileMissing:
            raise NotFound("User profile not found.")
        return Response(RedemptionSerializer(redemption).data, status=201)


class CatalogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardCatalog
        fields = ["reward_type", "point_cost"]
        read_only_fields = fields


class CatalogPagination(V1CursorPagination):
    ordering = ("point_cost", "id")


class V1RewardCatalogView(V1ListAPIView):
    """GET /api/v1/rewards/catalog - what can be redeemed, and for how much."""

    serializer_class = CatalogEntrySerializer
    pagination_class = CatalogPagination

    def get_queryset(self):
        return RewardCatalog.objects.filter(is_active=True)


class V1RedemptionListView(V1ListAPIView):
    """GET /api/v1/rewards/redemptions - the caller's own redemptions only."""

    serializer_class = RedemptionSerializer

    def get_queryset(self):
        return Redemption.objects.filter(user=self.request.user)
