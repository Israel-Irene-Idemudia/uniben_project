from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Redemption
from .serializers import RedemptionSerializer
from accounts.models import UserProfile

class RedeemRewardAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = RedemptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        point_cost = request.data.get('point_cost', 50)
        try:
            point_cost = int(point_cost)
        except ValueError:
            return Response({'error': 'Invalid point cost format.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get profile and check points
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            return Response({'error': 'User profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        if profile.points < point_cost:
            return Response(
                {'error': f'Insufficient points. You have {profile.points} points, but this costs {point_cost}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Deduct points
        profile.points -= point_cost
        profile.save()

        # Update profile phone and network if they are provided and weren't set yet
        phone = serializer.validated_data.get('phone')
        network = serializer.validated_data.get('network')
        if phone:
            profile.phone = phone
        if network:
            profile.network = network
        profile.save()

        # Save redemption log
        redemption = serializer.save(user=request.user, point_cost=point_cost, status='pending')
        
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
