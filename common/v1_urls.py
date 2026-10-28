"""Root of the /api/v1/ surface (mounted in uniben_portal/urls.py).

Each feature app adds its own v1 routes here with
    path("", include("<app>.v1_urls"))
Every view reachable from this module must use V1ViewMixin (tested).
"""
from django.urls import include, path

from common.health import HealthView, ReadyView

urlpatterns = [
    # Public liveness and readiness checks (Phase 1, task 1.9).
    # Both the slash and no-slash forms are accepted (tested).
    path("health", HealthView.as_view(), name="v1-health"),
    path("health/", HealthView.as_view()),
    path("ready", ReadyView.as_view(), name="v1-ready"),
    path("ready/", ReadyView.as_view()),
    path("", include("core.v1_urls")),
]