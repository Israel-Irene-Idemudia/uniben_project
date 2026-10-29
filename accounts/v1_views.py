import logging

from django.db import transaction
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response

from accounts.handoff import HandoffError, create_handoff_token, exchange_handoff_token
from accounts.services import DepartmentChangeError, change_department
from accounts.v1_profile import me_payload, profile_for, progress_payload
from accounts.v1_serializers import (
    DepartmentChangeSerializer,
    HandoffExchangeSerializer,
    MeUpdateSerializer,
)
from common.exceptions import ConflictError
from common.throttling import V1AuthThrottle
from common.views import PublicV1APIView, V1APIView

logger = logging.getLogger(__name__)

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


class DepartmentChangeView(V1APIView):
    """Change department (BE-02.2): once per semester unless an admin approves."""

    def post(self, request):
        serializer = DepartmentChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile_for(request.user)  # make sure a profile row exists
        try:
            change_department(
                request.user, data["department"], data["level"], reason=data.get("reason", "")
            )
        except DepartmentChangeError as exc:
            if exc.code == "same_department":
                raise ValidationError({"department_id": [exc.message]})
            raise ConflictError(exc.message)
        return Response(me_payload(profile_for(request.user)))


class WorldHandoffCreateView(V1APIView):
    """The Flutter app asks for a one-time key to open the web world (BE-01.3).

    Signed-in students only. Strict per-student rate limit (the auth scope).
    """

    throttle_classes = [V1AuthThrottle]

    def post(self, request):
        raw, ttl = create_handoff_token(request.user)
        response = Response({"token": raw, "expires_in": ttl}, status=201)
        response["Cache-Control"] = "no-store"
        return response


class WorldHandoffExchangeView(PublicV1APIView):
    """The web world swaps the one-time key for a normal session.

    Public on purpose (the web client has no session yet). It keeps the
    default per-IP limit, not the strict one: the key is 256 random bits so it
    cannot be guessed, and behind the proxy every student shares one IP (D-10),
    so a strict per-IP limit would only lock real students out.
    """

    def post(self, request):
        serializer = HandoffExchangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, access, refresh = exchange_handoff_token(serializer.validated_data["token"])
        except HandoffError:
            # Never log the key itself.
            logger.warning("World hand-off exchange rejected")
            raise ParseError("This hand-off link is invalid or has expired.")
        response = Response(
            {
                "access": access,
                "refresh": refresh,
                "user": {"id": user.id, "username": user.username},
            }
        )
        response["Cache-Control"] = "no-store"
        return response