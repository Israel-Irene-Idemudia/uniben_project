from django.urls import include, path
from rest_framework.response import Response

from common.views import PublicV1APIView, V1APIView


class ProtectedPing(V1APIView):
    def get(self, request):
        return Response({"ok": True})


class PublicPing(PublicV1APIView):
    def get(self, request):
        return Response({"ok": True})


urlpatterns = [
    path("api/v1/_test/protected/", ProtectedPing.as_view()),
    path("api/v1/_test/public/", PublicPing.as_view()),
    path("", include("uniben_portal.urls")),
]