"""Holds the current request's ID so log lines and error bodies can share it."""
import logging
from contextvars import ContextVar

_request_id: ContextVar = ContextVar("request_id", default=None)


def set_request_id(value):
    return _request_id.set(value)


def reset_request_id(token):
    _request_id.reset(token)


def get_request_id():
    return _request_id.get()


class RequestIDFilter(logging.Filter):
    """Adds `request_id` to every log record ('-' outside a request)."""

    def filter(self, record):
        record.request_id = get_request_id() or "-"
        return True