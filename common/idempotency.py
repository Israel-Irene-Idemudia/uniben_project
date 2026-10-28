"""Idempotency for v1 write endpoints (API-04).

Usage, on the HTTP method of a V1 view:

    class RedeemView(V1APIView):
        @idempotent
        def post(self, request):
            ...

Rules:
- The `Idempotency-Key` header is required.
- Keys are scoped to (user, method + path). Same key, same request: the stored
  response is replayed (header `Idempotent-Replayed: true`) and the view does
  not run again. Same key, different request: 409 conflict.
- Only 2xx responses are stored. A 4xx, a 5xx or an exception releases the key
  so the client can correct the request and retry with the same key.
- The key row and the view's own writes commit in ONE transaction. On
  PostgreSQL a parallel duplicate waits on the unique index until the first
  request finishes, then replays its response.
- An exception rolls back the view's writes; a 4xx RESPONSE keeps them (so a
  view can still record, say, a rejected attempt).
- This protects retries at the HTTP layer only. Awards stay safe because the
  XP ledger enforces its own unique idempotency key (BE-04.3).
"""
import hashlib
import json
import re
from functools import wraps

from django.db import IntegrityError, transaction
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework.utils.encoders import JSONEncoder

from common.exceptions import ConflictError
from common.models import IdempotencyKey

HEADER = "Idempotency-Key"
_VALID_KEY = re.compile(r"[A-Za-z0-9._:\-]{1,128}")


def _read_key(request):
    key = request.headers.get(HEADER, "")
    if not key:
        raise ValidationError({HEADER: ["This header is required."]})
    if not _VALID_KEY.fullmatch(key):
        raise ValidationError(
            {HEADER: ["Use 1 to 128 letters, digits, dots, dashes, underscores or colons."]}
        )
    return key


def _hash_request(request, endpoint):
    body = request.data
    if hasattr(body, "lists"):  # form / multipart QueryDict
        body = {name: values for name, values in body.lists()}
    payload = json.dumps(
        {
            "endpoint": endpoint,
            "query": sorted(request.query_params.lists()),
            "body": body,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _jsonable(data):
    return json.loads(json.dumps(data, cls=JSONEncoder))


def _claim(user, endpoint, key, request_hash):
    """Insert the key row. Returns None if someone already holds it."""
    try:
        with transaction.atomic():  # savepoint, so a clash does not poison the outer transaction
            return IdempotencyKey.objects.create(
                user=user, endpoint=endpoint, key=key, request_hash=request_hash
            )
    except IntegrityError:
        return None


def _replay(user, endpoint, key, request_hash):
    try:
        existing = IdempotencyKey.objects.get(user=user, endpoint=endpoint, key=key)
    except IdempotencyKey.DoesNotExist:
        raise ConflictError("Please retry this request.")
    if existing.request_hash != request_hash:
        raise ConflictError("This Idempotency-Key was already used for a different request.")
    response = Response(existing.response_body, status=existing.response_status)
    response["Idempotent-Replayed"] = "true"
    return response


def idempotent(view_method):
    @wraps(view_method)
    def wrapper(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise NotAuthenticated()
        key = _read_key(request)
        endpoint = f"{request.method} {request.path}"
        request_hash = _hash_request(request, endpoint)

        with transaction.atomic():
            record = _claim(user, endpoint, key, request_hash)
            if record is None:
                return _replay(user, endpoint, key, request_hash)

            response = view_method(self, request, *args, **kwargs)
            if 200 <= response.status_code < 300:
                record.response_status = response.status_code
                record.response_body = _jsonable(response.data)
                record.save(update_fields=["response_status", "response_body"])
            else:
                record.delete()
            return response

    return wrapper