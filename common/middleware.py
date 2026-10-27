import re
import uuid

from common.request_context import reset_request_id, set_request_id

# Why validate: a client may send its own ID to correlate its logs with ours,
# but an unchecked value could inject fake log lines or break log parsing.
# Anything outside this strict pattern is ignored and replaced.
_SAFE_ID = re.compile(r"[A-Za-z0-9._\-]{1,64}")


class RequestIDMiddleware:
    """Gives every request an ID, logs it, and returns it as X-Request-ID."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get("HTTP_X_REQUEST_ID", "")
        request_id = incoming if _SAFE_ID.fullmatch(incoming) else str(uuid.uuid4())
        request.request_id = request_id

        token = set_request_id(request_id)
        try:
            response = self.get_response(request)
        finally:
            reset_request_id(token)

        response["X-Request-ID"] = request_id
        return response