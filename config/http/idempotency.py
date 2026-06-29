"""Règle 3 — Idempotency-Key sur POST (cache réponse, 409 si en cours)."""
from __future__ import annotations

import hashlib
import json
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

HEADER = 'Idempotency-Key'
TTL = getattr(settings, 'IDEMPOTENCY_TTL_SECONDS', 86400)
LOCK_TTL = getattr(settings, 'IDEMPOTENCY_LOCK_SECONDS', 120)


def _cache_key(request, idem_key: str) -> str:
    user_id = getattr(getattr(request, 'user', None), 'pk', 'anon')
    path = request.path or ''
    raw = f'{user_id}:{request.method}:{path}:{idem_key}'
    return 'idem:' + hashlib.sha256(raw.encode()).hexdigest()


class IdempotencyMiddleware:
    """POST /api/* avec Idempotency-Key — rejoue la réponse en cache."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method != 'POST' or not (request.path or '').startswith('/api/'):
            return self.get_response(request)

        idem_key = (request.META.get(f'HTTP_{HEADER.upper().replace("-", "_")}') or '').strip()
        if not idem_key:
            return self.get_response(request)

        cache_key = _cache_key(request, idem_key)
        lock_key = cache_key + ':lock'

        cached = cache.get(cache_key)
        if cached:
            return _replay_cached(cached)

        if cache.add(lock_key, '1', LOCK_TTL) is False:
            return HttpResponse(
                content=json.dumps({
                    'type': 'urn:uhakika:problem:idempotency-in-progress',
                    'title': 'Conflict',
                    'status': 409,
                    'detail': 'Requête idempotente déjà en cours de traitement.',
                    'instance': request.build_absolute_uri(),
                }),
                status=409,
                content_type='application/problem+json',
            )

        try:
            response = self.get_response(request)
        finally:
            cache.delete(lock_key)

        if response.status_code in (200, 201, 202, 204):
            cache.set(
                cache_key,
                {
                    'status': response.status_code,
                    'headers': {
                        k: v for k, v in response.items()
                        if k.lower() not in ('set-cookie', 'transfer-encoding')
                    },
                    'body': response.content.decode('utf-8', errors='replace') if response.content else '',
                    'content_type': response.get('Content-Type', 'application/json'),
                },
                TTL,
            )
        return response


def _replay_cached(payload: dict) -> HttpResponse:
    response = HttpResponse(
        content=payload.get('body', ''),
        status=payload.get('status', 200),
        content_type=payload.get('content_type', 'application/json'),
    )
    for key, val in (payload.get('headers') or {}).items():
        if key.lower() not in ('content-length', 'content-type'):
            response[key] = val
    response['Idempotency-Replayed'] = 'true'
    return response
