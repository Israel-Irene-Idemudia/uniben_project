"""The one v1 error shape (API-06):

    {"code": "...", "message": "...", "field_errors": {...}, "request_id": "..."}

Applied per view through V1ViewMixin.get_exception_handler, NOT through the
global REST_FRAMEWORK setting, so live legacy endpoints keep their old
{"detail": ...} responses.
"""
import logging

from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.request_context import get_request_id

logger = logging.getLogger(__name__)

VALIDATION_MESSAGE = "Please correct the highlighted fields."
SERVER_ERROR_MESSAGE = "Something went wrong on our side. Please try again."

_CODE_BY_STATUS = {
    400: "bad_request",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    406: "not_acceptable",
    409: "conflict",
    415: "unsupported_media_type",
    429: "rate_limited",
    503: "service_unavailable",
}


class ConflictError(APIException):
    """409. Used by idempotency (same key, different request body)."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "This request conflicts with an earlier one."
    default_code = "conflict"

class ServiceUnavailable(APIException):
    """503. Used by the readiness check when a dependency is down."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"


def _body(code, message, request_id, field_errors=None):
    return {
        "code": code,
        "message": message,
        "field_errors": field_errors or {},
        "request_id": request_id,
    }


def _normalize(detail):
    """Turn DRF ErrorDetail structures into plain strings/lists/dicts."""
    if isinstance(detail, dict):
        return {key: _normalize(value) for key, value in detail.items()}
    if isinstance(detail, (list, tuple)):
        return [_normalize(item) for item in detail]
    return str(detail)


def _request_id_from(context):
    request = context.get("request")
    return getattr(request, "request_id", None) or get_request_id()


def v1_exception_handler(exc, context):
    request_id = _request_id_from(context)
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled error. Log the real cause with the request ID so it can be
        # found from the ID a student reports; never leak it in the response.
        logger.error("Unhandled exception in v1 view", exc_info=exc)
        return Response(
            _body("server_error", SERVER_ERROR_MESSAGE, request_id),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        detail = _normalize(exc.detail)
        field_errors = detail if isinstance(detail, dict) else {"non_field_errors": detail}
        response.data = _body("validation_error", VALIDATION_MESSAGE, request_id, field_errors)
        return response

    data = response.data if isinstance(response.data, dict) else {}
    message = str(data.get("detail") or "Request failed.")
    code = _CODE_BY_STATUS.get(response.status_code, "error")
    if isinstance(exc, AuthenticationFailed) and isinstance(data.get("code"), str):
        # SimpleJWT sends e.g. "token_not_valid"; clients use it to decide
        # whether to refresh the token.
        code = data["code"]

    response.data = _body(code, message, request_id)
    return response