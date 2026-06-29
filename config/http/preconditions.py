"""Règle 2 — If-Match / 412 Precondition Failed sur PUT, PATCH, DELETE."""
from __future__ import annotations

from functools import wraps

from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from config.http.etag import compute_resource_etag, etags_match
from config.http.problem_details import problem_response


def _check_if_match(request, view, instance):
    if_match = request.META.get('HTTP_IF_MATCH', '').strip()
    if not if_match:
        # Pas encore exigé côté frontend : pas de blocage si absent.
        return None
    current = compute_resource_etag(view, instance, request)
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


def _attach_etag_header(response, view, instance, request):
    if getattr(response, 'status_code', None) not in (200, 201):
        return response
    try:
        instance.refresh_from_db()
        response['ETag'] = compute_resource_etag(view, instance, request)
    except Exception:
        pass
    return response


def _wrap_mutating(method_name):
    original = getattr(ModelViewSet, method_name)

    @wraps(original)
    def wrapper(self, request, *args, **kwargs):
        if request.method in ('PUT', 'PATCH', 'DELETE') and (request.path or '').startswith('/api/'):
            instance = None
            try:
                instance = self.get_object()
            except Exception:
                return original(self, request, *args, **kwargs)
            failed = _check_if_match(request, self, instance)
            if failed is not None:
                return failed
            response = original(self, request, *args, **kwargs)
            if request.method in ('PUT', 'PATCH') and instance is not None:
                return _attach_etag_header(response, self, instance, request)
            return response
        return original(self, request, *args, **kwargs)

    return wrapper


def apply_precondition_patches():
    for name in ('update', 'partial_update', 'destroy'):
        if not getattr(ModelViewSet, name).__name__.startswith('_uhakika'):
            wrapped = _wrap_mutating(name)
            wrapped.__name__ = f'_uhakika_{name}'
            setattr(ModelViewSet, name, wrapped)
