"""Règle 1 — ETag / If-None-Match / 304 Not Modified."""
from __future__ import annotations

import hashlib

from django.http import HttpResponse

from config.http.streaming import ranged_bytes_response


def compute_weak_etag(content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f'W/"{digest}"'


def compute_serialized_etag(data) -> str:
    """ETag identique à celui produit par ETagMiddleware sur une réponse JSON DRF."""
    from rest_framework.renderers import JSONRenderer

    body = JSONRenderer().render(data)
    return compute_weak_etag(body)


def compute_resource_etag(view, instance, request=None) -> str:
    """
    ETag d'une ressource API — aligné sur le corps JSON GET (If-None-Match / If-Match).
    """
    get_serializer = getattr(view, 'get_serializer', None)
    if get_serializer is not None:
        try:
            serializer = get_serializer(instance)
            return compute_serialized_etag(serializer.data)
        except Exception:
            pass
    return compute_instance_etag(instance)


def normalize_etag(value: str) -> str:
    return (value or '').strip().strip('"').replace('W/', '').replace('w/', '')


def etags_match(client_value: str, server_etag: str) -> bool:
    if not client_value:
        return False
    server_norm = normalize_etag(server_etag)
    for part in client_value.split(','):
        part = part.strip()
        if part == '*':
            return True
        if normalize_etag(part) == server_norm:
            return True
    return False


class ETagMiddleware:
    """GET /api/* — ETag sur le corps ; 304 si If-None-Match correspond."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method != 'GET':
            return response
        path = request.path or ''
        if not path.startswith('/api/'):
            return response
        if response.status_code != 200:
            return response
        if getattr(response, 'streaming', False):
            return response

        content_type = (response.get('Content-Type') or '').lower()
        is_json = 'application/json' in content_type or 'application/problem+json' in content_type
        is_binary = 'application/pdf' in content_type or 'text/csv' in content_type

        if not is_json and not is_binary:
            return response

        body = response.content
        if is_binary and request.META.get('HTTP_RANGE', '').strip():
            ranged = ranged_bytes_response(
                request,
                body,
                content_type.split(';')[0].strip(),
            )
            for key in ('X-Correlation-ID', 'Content-Language', 'API-Version'):
                if key in response:
                    ranged[key] = response[key]
            return ranged

        etag = compute_weak_etag(body)
        response['ETag'] = etag
        inm = request.META.get('HTTP_IF_NONE_MATCH', '')
        if etags_match(inm, etag):
            not_modified = HttpResponse(status=304)
            not_modified['ETag'] = etag
            for key in ('X-Correlation-ID', 'Content-Language', 'API-Version'):
                if key in response:
                    not_modified[key] = response[key]
            return not_modified
        return response


def compute_instance_etag(instance) -> str:
    """ETag faible pour If-Match (optimistic locking) — repli si pas de serializer."""
    parts = [
        instance.__class__.__name__,
        str(getattr(instance, 'pk', '')),
    ]
    for attr in (
        'updated_at',
        'date_modification',
        'date_creation',
        'statut',
        'configuration_complete',
        'config',
    ):
        val = getattr(instance, attr, None)
        if val is not None:
            parts.append(str(val))
    raw = ':'.join(parts).encode('utf-8')
    return compute_weak_etag(raw)
