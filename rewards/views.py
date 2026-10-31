from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Redemption
from .serializers import RedemptionSerializer
from .services import ProfileMissing, UnknownReward, redeem_reward
from xp.services import InsufficientPoints


class RedeemInputSerializer(serializers.Serializer):
    """What a client may send to redeem. `point_cost` is deliberately NOT a
    field: DRF drops unknown keys, so any price a client sends is ignored and
    the catalogue price is charged (D-1, D7).

    DECISION: a stale or tampered point_cost is silently ignored, not
    rejected, so older Flutter builds that still send one keep working.
    """

    reward_type = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    network = serializers.CharField(max_length=20)


class RedeemRewardAPI(APIView):
    """LEGACY /api/rewards/redeem/ - same request and response shapes as before."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RedeemInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        try:
            redemption = redeem_reward(
                request.user,
                reward_type=data["reward_type"],
                phone=data["phone"],
                network=data["network"],
            )
        except UnknownReward:
            return Response({'error': 'This reward is not available.'}, status=status.HTTP_400_BAD_REQUEST)
        except ProfileMissing:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        except InsufficientPoints as exc:
            return Response(
                {'error': f'Insufficient points. You have {exc.balance} points, but this costs {exc.cost}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(RedemptionSerializer(redemption).data, status=status.HTTP_201_CREATED)


class UserRedemptionListAPI(generics.ListAPIView):
    serializer_class = RedemptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Redemption.objects.filter(user=self.request.user).order_by('-created_at')


class AdminRedemptionListAPI(generics.ListAPIView):
    serializer_class = RedemptionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Redemption.objects.all().order_by('-created_at')
        status_param = self.request.query_params.get('status')
        if status_param in ['pending', 'dispatched']:
            qs = qs.filter(status=status_param)
        return qs


class AdminRedemptionDispatchAPI(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        redemption = get_object_or_404(Redemption, pk=pk)
        new_status = request.data.get('status', 'dispatched')
        
        if new_status not in ['pending', 'dispatched']:
            return Response({'error': 'Invalid status choice.'}, status=status.HTTP_400_BAD_REQUEST)

        redemption.status = new_status
        redemption.save()

        return Response(RedemptionSerializer(redemption).data, status=status.HTTP_200_OK)
