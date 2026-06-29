"""Règle 6 — Version API via en-tête Accept (pas de /v1/ dans l'URL)."""
from __future__ import annotations

import re

DEFAULT_API_VERSION = '1.0'
SUPPORTED_API_VERSIONS = ('1.0', '2.0')

_ACCEPT_VERSION_RE = re.compile(
    r'application/(?:[\w.+-]+\+)?json(?:;\s*version\s*=\s*([\d.]+))?',
    re.IGNORECASE,
)


class ApiVersionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        version = DEFAULT_API_VERSION
        accept = request.META.get('HTTP_ACCEPT') or ''
        for part in accept.split(','):
            part = part.strip()
            m = _ACCEPT_VERSION_RE.search(part)
            if m:
                candidate = (m.group(1) or DEFAULT_API_VERSION).strip()
                if candidate in SUPPORTED_API_VERSIONS:
                    version = candidate
                break
        request.api_version = version
        response = self.get_response(request)
        if (request.path or '').startswith('/api/'):
            response['API-Version'] = version
        return response


def get_api_version(request) -> str:
    return getattr(request, 'api_version', DEFAULT_API_VERSION)
