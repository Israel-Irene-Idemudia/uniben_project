from django.http import Http404
from django.urls import include, path
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, Throttled
from rest_framework.response import Response

from common.exceptions import ConflictError
from common.views import PublicV1APIView, V1APIView


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


urlpatterns = [
    path("api/v1/_test/protected/", ProtectedPing.as_view()),
    path("api/v1/_test/public/", PublicPing.as_view()),
    path("api/v1/_test/validate/", ValidateView.as_view()),
    path("api/v1/_test/forbidden/", ForbiddenView.as_view()),
    path("api/v1/_test/notfound/", NotFoundView.as_view()),
    path("api/v1/_test/conflict/", ConflictView.as_view()),
    path("api/v1/_test/throttled/", ThrottledView.as_view()),
    path("api/v1/_test/boom/", BoomView.as_view()),
    path("", include("uniben_portal.urls")),
]