"""Middleware : blocage opérations métier si configuration incomplète."""
from django.http import JsonResponse
from django.utils.translation import gettext as _

from abonnements.controle_licence import controle_licence_actif
from abonnements.middleware import PROBLEM_JSON, _authentifier_jwt_si_bearer
from inscription.controle_metier import doit_bloquer_configuration_metier


class ControleConfigurationMetierMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not controle_licence_actif():
            return self.get_response(request)

        _authentifier_jwt_si_bearer(request)

        bloquer, code, detail = doit_bloquer_configuration_metier(request)
        if bloquer:
            body = {
                'type': f'urn:uhakika:problem:{code}',
                'title': _('Configuration incomplète'),
                'status': 403,
                'detail': detail,
                'code': code,
                'action_recommandee': 'completer_configuration',
            }
            response = JsonResponse(body, status=403, content_type=PROBLEM_JSON)
            response['Content-Type'] = PROBLEM_JSON
            return response

        return self.get_response(request)
