"""Pagination for /api/v1/ (decision D-4, API-03).

- V1CursorPagination: feeds, ledgers, anything that grows. Stable while rows
  are being added, and cheap on large tables. Returns a bare `next_cursor`
  token rather than a URL: behind nginx this project's Django does not know
  the request was HTTPS, so DRF-built absolute links would use http://.
- V1PageNumberPagination: small admin lists only.

Both are opt-in per view (never global), so legacy list endpoints are not
affected.
"""
from urllib.parse import parse_qs, urlparse

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response


class V1CursorPagination(CursorPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    # Newest first, with id as a tie-breaker so rows written in the same
    # instant (common for ledger entries) still have one stable order.
    # Subclass and change `ordering` for a different sort.
    ordering = ("-created_at", "-id")

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view)
        except NotFound:
            raise ValidationError({self.cursor_query_param: ["Invalid cursor."]})

    def _cursor_token(self, link):
        if not link:
            return None
        values = parse_qs(urlparse(link).query).get(self.cursor_query_param)
        return values[0] if values else None

    def get_paginated_response(self, data):
        return Response(
            {
                "results": data,
                "next_cursor": self._cursor_token(self.get_next_link()),
            }
        )


class V1PageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view)
        except NotFound:
            raise ValidationError({self.page_query_param: ["Invalid page."]})

    def get_paginated_response(self, data):
        paginator = self.page.paginator
        return Response(
            {
                "count": paginator.count,
                "page": self.page.number,
                "page_size": paginator.per_page,
                "total_pages": paginator.num_pages,
                "results": data,
            }
        )