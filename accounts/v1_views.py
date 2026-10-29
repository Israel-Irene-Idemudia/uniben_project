from django.db import transaction
from rest_framework.response import Response

from accounts.v1_profile import me_payload, profile_for, progress_payload
from accounts.v1_serializers import MeUpdateSerializer
from common.views import V1APIView

_USER_FIELDS = ("first_name", "last_name")
_PROFILE_FIELDS = ("phone", "network", "student_id", "matric_number")


class MeView(V1APIView):
    """The signed-in student's own profile."""

    def get(self, request):
        return Response(me_payload(profile_for(request.user)))

    def patch(self, request):
        serializer = MeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile = profile_for(request.user)
        with transaction.atomic():
            user = request.user
            for field in _USER_FIELDS:
                if field in data:
                    setattr(user, field, data[field])
            if any(f in data for f in _USER_FIELDS):
                user.save(update_fields=[f for f in _USER_FIELDS if f in data])
            for field in _PROFILE_FIELDS:
                if field in data:
                    setattr(profile, field, data[field])
            if any(f in data for f in _PROFILE_FIELDS):
                profile.save(update_fields=[f for f in _PROFILE_FIELDS if f in data])
        return Response(me_payload(profile_for(request.user)))


class MeProgressView(V1APIView):
    """'How do I progress?' (BE-02.4). Ledger fields fill in from Phase 3."""

    def get(self, request):
        return Response(progress_payload(profile_for(request.user)))