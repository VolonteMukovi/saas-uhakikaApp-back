"""Règle 5 — RFC 9457 Problem Details (application/problem+json)."""
from __future__ import annotations

from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from caisse.services.caisse_defaut import CaisseError
from caisse.services.errors import validation_error_message
from caisse.services.session_caisse import SessionCaisseError

PROBLEM_CONTENT_TYPE = 'application/problem+json'
DEFAULT_PROBLEM_TYPE = 'about:blank'


def problem_response(
    *,
    request,
    status_code: int,
    title: str,
    detail: str,
    type_uri: str = DEFAULT_PROBLEM_TYPE,
    extra: dict | None = None,
) -> Response:
    instance = request.build_absolute_uri() if request else ''
    body = {
        'type': type_uri,
        'title': title,
        'status': status_code,
        'detail': detail,
        'instance': instance,
    }
    if extra:
        body.update(extra)
    response = Response(body, status=status_code, content_type=PROBLEM_CONTENT_TYPE)
    response['Content-Type'] = PROBLEM_CONTENT_TYPE
    return response


def _status_title(code: int) -> str:
    try:
        return HttpResponse.status_code_to_reason_phrase(code) or 'Error'
    except Exception:
        return 'Error'


def _validation_errors_to_detail(data) -> str:
    if isinstance(data, dict):
        if 'detail' in data and len(data) == 1:
            return str(data['detail'])
        parts = []
        for key, val in data.items():
            if isinstance(val, (list, tuple)):
                parts.append(f'{key}: {"; ".join(str(v) for v in val)}')
            else:
                parts.append(f'{key}: {val}')
        return ' | '.join(parts) if parts else 'Validation error'
    return str(data)


def exception_handler(exc, context):
    request = context.get('request')

    if isinstance(exc, (SessionCaisseError, CaisseError)):
        return problem_response(
            request=request,
            status_code=status.HTTP_400_BAD_REQUEST,
            title='Caisse Error',
            detail=validation_error_message(exc),
            type_uri='urn:uhakika:problem:caisse-error',
        )

    from abonnements.exceptions import FonctionnaliteNonAutorisee, LicenceInactive, LimiteQuotaAtteinte

    if isinstance(exc, LicenceInactive):
        extra = {
            'code': exc.default_code,
            'etat_licence': getattr(exc, 'etat_licence', {}),
            'action_recommandee': 'renouveler_abonnement',
        }
        return problem_response(
            request=request,
            status_code=exc.status_code,
            title='Licence inactive',
            detail=str(exc.detail),
            type_uri='urn:uhakika:problem:licence-inactive',
            extra=extra,
        )

    if isinstance(exc, FonctionnaliteNonAutorisee):
        return problem_response(
            request=request,
            status_code=exc.status_code,
            title='Fonctionnalité non autorisée',
            detail=str(exc.detail),
            type_uri='urn:uhakika:problem:fonctionnalite-non-autorisee',
            extra={
                'code': exc.default_code,
                'action_recommandee': 'changer_formule',
                'url_formules': '/api/abonnements/formules/',
            },
        )


    if isinstance(exc, LimiteQuotaAtteinte):
        return problem_response(
            request=request,
            status_code=exc.status_code,
            title='Limite de formule atteinte',
            detail=str(exc.detail),
            type_uri='urn:uhakika:problem:limite-quota',
            extra={
                'code': exc.default_code,
                'type_quota': getattr(exc, 'type_quota', None),
                'maximum': getattr(exc, 'maximum', None),
                'actuel': getattr(exc, 'actuel', None),
                'action_recommandee': 'changer_formule',
            },
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    status_code = response.status_code
    data = response.data

    if isinstance(exc, APIException) and isinstance(data, dict) and 'detail' in data and len(data) == 1:
        detail = str(data['detail'])
        extra = None
    elif isinstance(data, dict):
        detail = _validation_errors_to_detail(data)
        extra = {'errors': data} if status_code == status.HTTP_400_BAD_REQUEST else None
        if extra is not None:
            for key in ('code', 'entreprise_id'):
                if key in data:
                    extra[key] = data[key]
    else:
        detail = str(data)
        extra = None

    title = _status_title(status_code)
    if isinstance(exc, APIException) and getattr(exc, 'default_code', None):
        type_uri = f'urn:uhakika:problem:{exc.default_code}'
    else:
        type_uri = DEFAULT_PROBLEM_TYPE

    return problem_response(
        request=request,
        status_code=status_code,
        title=title,
        detail=detail,
        type_uri=type_uri,
        extra=extra,
    )
