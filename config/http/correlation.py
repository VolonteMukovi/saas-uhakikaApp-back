"""Règle 8 — X-Correlation-ID traçabilité."""
from __future__ import annotations

import contextvars
import logging
import uuid

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    'correlation_id', default=None,
)


def get_correlation_id() -> str | None:
    return correlation_id_var.get()


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = get_correlation_id() or '-'
        return True


class CorrelationIdMiddleware:
    HEADER = 'X-Correlation-ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cid = (request.META.get(f'HTTP_{self.HEADER.upper().replace("-", "_")}') or '').strip()
        if not cid:
            cid = str(uuid.uuid4())
        request.correlation_id = cid
        token = correlation_id_var.set(cid)
        try:
            response = self.get_response(request)
        finally:
            correlation_id_var.reset(token)
        response[self.HEADER] = cid
        return response
