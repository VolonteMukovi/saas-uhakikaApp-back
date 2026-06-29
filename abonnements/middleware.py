"""
Middleware licence SaaS :
1. Enrichit la requête JWT (user, tenant, etat_licence) avant les vues DRF.
2. Bloque les écritures si la licence entreprise n'est pas active.
"""
from django.http import JsonResponse
from django.utils.translation import gettext as _

from abonnements.controle_licence import (
    controle_licence_actif,
    doit_bloquer_ecriture,
    message_blocage_licence,
)
from abonnements.services.licence import build_etat_licence

PROBLEM_JSON = 'application/problem+json'


def _authentifier_jwt_si_bearer(request):
    """
    DRF n'authentifie le JWT qu'au moment de la vue.
    On réutilise JWTAuthenticationWithContext pour disposer de tenant_id / etat_licence ici.
    """
    if getattr(request, '_jwt_enrichi', False):
        return
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return
    from users.authentication import JWTAuthenticationWithContext

    try:
        auth = JWTAuthenticationWithContext()
        result = auth.authenticate(request)
        if result:
            request.user, _token = result
            request._jwt_enrichi = True
    except Exception:
        pass


def _attacher_etat_licence(request):
    if getattr(request, 'etat_licence', None) is not None:
        return
    request.etat_licence = None
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or user.is_superuser:
        return
    eid = getattr(request, 'tenant_id', None) or user.get_entreprise_id(request)
    if eid:
        request.etat_licence = build_etat_licence(eid)


class LicenceEntrepriseMiddleware:
    """Enrichit request.etat_licence (JWT + session)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _authentifier_jwt_si_bearer(request)
        _attacher_etat_licence(request)
        response = self.get_response(request)
        return response


class ControleLicenceEcritureMiddleware:
    """Bloque POST/PUT/PATCH/DELETE si licence inactive (lecture seule)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not controle_licence_actif():
            return self.get_response(request)

        _authentifier_jwt_si_bearer(request)
        _attacher_etat_licence(request)

        bloquer, etat = doit_bloquer_ecriture(request)
        if bloquer:
            detail = message_blocage_licence(etat)
            body = {
                'type': 'urn:uhakika:problem:licence-inactive',
                'title': _('Licence inactive'),
                'status': 403,
                'detail': detail,
                'code': 'licence_inactive',
                'etat_licence': {
                    'statut': etat.get('statut') if etat else 'aucun',
                    'est_actif': False,
                    'formule_code': etat.get('formule_code') if etat else None,
                    'formule_nom': etat.get('formule_nom') if etat else None,
                    'jours_restants': etat.get('jours_restants') if etat else 0,
                    'date_fin': (
                        etat.get('date_fin').isoformat()
                        if etat and etat.get('date_fin') else None
                    ),
                },
                'action_recommandee': 'renouveler_abonnement',
                'url_renouvellement': '/api/abonnements/formules/',
            }
            response = JsonResponse(body, status=403, content_type=PROBLEM_JSON)
            response['Content-Type'] = PROBLEM_JSON
            return response

        return self.get_response(request)


def _reponse_probleme_plan(request, *, code: str, title: str, detail: str, type_uri: str, extra: dict):
    body = {
        'type': type_uri,
        'title': title,
        'status': 403,
        'detail': detail,
        'code': code,
        **extra,
    }
    response = JsonResponse(body, status=403, content_type=PROBLEM_JSON)
    response['Content-Type'] = PROBLEM_JSON
    return response


class ControleFonctionnalitePlanMiddleware:
    """Bloque accès aux fonctionnalités non incluses dans la formule (étape 4)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not controle_licence_actif():
            return self.get_response(request)

        _authentifier_jwt_si_bearer(request)
        _attacher_etat_licence(request)

        from abonnements.exceptions import FonctionnaliteNonAutorisee, LimiteQuotaAtteinte
        from abonnements.services.limites import doit_bloquer_fonctionnalite_plan

        try:
            bloquer, cle, etat = doit_bloquer_fonctionnalite_plan(request)
        except FonctionnaliteNonAutorisee as exc:
            return _reponse_probleme_plan(
                request,
                code='fonctionnalite_non_autorisee',
                title=_('Fonctionnalité non autorisée'),
                detail=str(exc.detail),
                type_uri='urn:uhakika:problem:fonctionnalite-non-autorisee',
                extra={
                    'action_recommandee': 'changer_formule',
                    'url_formules': '/api/abonnements/formules/',
                },
            )
        except LimiteQuotaAtteinte as exc:
            return _reponse_probleme_plan(
                request,
                code='limite_quota_atteinte',
                title=_('Limite de formule atteinte'),
                detail=str(exc.detail),
                type_uri='urn:uhakika:problem:limite-quota',
                extra={
                    'type_quota': getattr(exc, 'type_quota', None),
                    'maximum': getattr(exc, 'maximum', None),
                    'actuel': getattr(exc, 'actuel', None),
                    'action_recommandee': 'changer_formule',
                    'url_formules': '/api/abonnements/formules/',
                },
            )

        if bloquer and cle:
            detail = _(
                'Cette fonctionnalité (%(feature)s) n\'est pas disponible dans votre formule « %(plan)s ». '
                'Veuillez passer à une formule supérieure pour l\'utiliser.'
            ) % {
                'feature': cle,
                'plan': (etat or {}).get('formule_nom') or (etat or {}).get('formule_code'),
            }
            return _reponse_probleme_plan(
                request,
                code='fonctionnalite_non_autorisee',
                title=_('Fonctionnalité non autorisée'),
                detail=detail,
                type_uri='urn:uhakika:problem:fonctionnalite-non-autorisee',
                extra={
                    'fonctionnalite': cle,
                    'formule_code': (etat or {}).get('formule_code'),
                    'action_recommandee': 'changer_formule',
                    'url_formules': '/api/abonnements/formules/',
                },
            )

        return self.get_response(request)
