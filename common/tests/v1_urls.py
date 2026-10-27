"""Root of the /api/v1/ surface (mounted in uniben_portal/urls.py).

Each feature app adds its own v1 routes here with
    path("", include("<app>.v1_urls"))
Every view reachable from this module must use V1ViewMixin (tested).
"""
urlpatterns = []