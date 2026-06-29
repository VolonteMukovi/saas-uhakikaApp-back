"""Règle 2 — If-Match / 412 Precondition Failed sur PUT, PATCH, DELETE."""
from __future__ import annotations

from functools import wraps

from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from config.http.etag import etags_match, compute_instance_etag
from config.http.problem_details import problem_response


def _check_if_match(request, instance):
    if_match = request.META.get('HTTP_IF_MATCH', '').strip()
    if not if_match:
        # Pas encore exigé côté frontend : pas de blocage si absent.
        return None
    current = compute_instance_etag(instance)
    if not etags_match(if_match, current):
        return problem_response(
            request=request,
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            title='Precondition Failed',
            detail='La ressource a été modifiée ailleurs. Rechargez puis réessayez.',
            type_uri='urn:uhakika:problem:precondition-failed',
            extra={'current_etag': current},
        )
    return None


def _wrap_mutating(method_name):
    original = getattr(ModelViewSet, method_name)

    @wraps(original)
    def wrapper(self, request, *args, **kwargs):
        if request.method in ('PUT', 'PATCH', 'DELETE') and (request.path or '').startswith('/api/'):
            try:
                instance = self.get_object()
            except Exception:
                return original(self, request, *args, **kwargs)
            failed = _check_if_match(request, instance)
            if failed is not None:
                return failed
        return original(self, request, *args, **kwargs)

    return wrapper


def apply_precondition_patches():
    for name in ('update', 'partial_update', 'destroy'):
        if not getattr(ModelViewSet, name).__name__.startswith('_uhakika'):
            wrapped = _wrap_mutating(name)
            wrapped.__name__ = f'_uhakika_{name}'
            setattr(ModelViewSet, name, wrapped)
