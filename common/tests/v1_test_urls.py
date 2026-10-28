from django.http import Http404
from django.urls import include, path
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, Throttled
from rest_framework.response import Response
from common.idempotency import idempotent

from accounts.models import UserTodoEntry
from common.exceptions import ConflictError
from common.pagination import V1CursorPagination
from common.views import (
    PublicV1APIView,
    V1AdminListAPIView,
    V1APIView,
    V1ListAPIView,
)


class ProtectedPing(V1APIView):
    def get(self, request):
        return Response({"ok": True})


class PublicPing(PublicV1APIView):
    def get(self, request):
        return Response({"ok": True})


class _Input(serializers.Serializer):
    name = serializers.CharField()


class ValidateView(V1APIView):
    def post(self, request):
        serializer = _Input(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class ForbiddenView(V1APIView):
    def get(self, request):
        raise PermissionDenied("You cannot do that.")


class NotFoundView(V1APIView):
    def get(self, request):
        raise Http404


class ConflictView(V1APIView):
    def get(self, request):
        raise ConflictError()


class ThrottledView(V1APIView):
    def get(self, request):
        raise Throttled(wait=5)


class BoomView(V1APIView):
    def get(self, request):
        raise RuntimeError("secret internal detail")


class _TodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTodoEntry
        fields = ["id", "task"]


class CursorList(V1ListAPIView):
    queryset = UserTodoEntry.objects.all()
    serializer_class = _TodoSerializer


class _TinyCursorPagination(V1CursorPagination):
    max_page_size = 5


class TinyCursorList(CursorList):
    pagination_class = _TinyCursorPagination


class PageList(V1AdminListAPIView):
    queryset = UserTodoEntry.objects.order_by("id")
    serializer_class = _TodoSerializer


class CreateTodoView(V1APIView):
    @idempotent
    def post(self, request):
        entry = UserTodoEntry.objects.create(
            user=request.user, task=request.data.get("task", "t")
        )
        return Response({"id": entry.id, "task": entry.task}, status=201)


class RejectingTodoView(V1APIView):
    @idempotent
    def post(self, request):
        UserTodoEntry.objects.create(user=request.user, task="attempt")
        return Response({"detail": "nope"}, status=400)


class ExplodingTodoView(V1APIView):
    @idempotent
    def post(self, request):
        UserTodoEntry.objects.create(user=request.user, task="doomed")
        raise RuntimeError("boom")

urlpatterns = [
    path("api/v1/_test/protected/", ProtectedPing.as_view()),
    path("api/v1/_test/public/", PublicPing.as_view()),
    path("api/v1/_test/validate/", ValidateView.as_view()),
    path("api/v1/_test/forbidden/", ForbiddenView.as_view()),
    path("api/v1/_test/notfound/", NotFoundView.as_view()),
    path("api/v1/_test/conflict/", ConflictView.as_view()),
    path("api/v1/_test/throttled/", ThrottledView.as_view()),
    path("api/v1/_test/boom/", BoomView.as_view()),
    path("api/v1/_test/cursor/", CursorList.as_view()),
    path("api/v1/_test/cursor-tiny/", TinyCursorList.as_view()),
    path("api/v1/_test/pages/", PageList.as_view()),
    path("api/v1/_test/todos/", CreateTodoView.as_view()),
    path("api/v1/_test/todos-b/", CreateTodoView.as_view()),
    path("api/v1/_test/todos-reject/", RejectingTodoView.as_view()),
    path("api/v1/_test/todos-explode/", ExplodingTodoView.as_view()),
    path("", include("uniben_portal.urls")),
]