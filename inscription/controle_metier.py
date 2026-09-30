"""Contrôle configuration entreprise / profil / onboarding avant opérations métier."""
from __future__ import annotations

from django.utils.translation import gettext as _

from abonnements.chemins_api import METHODES_LECTURE, chemin_setup_autorise
from abonnements.controle_licence import chemin_exempt, controle_licence_actif
from inscription.services.onboarding_status import (
    build_onboarding_status,
    message_blocage_onboarding,
    onboarding_metier_autorise,
)


def _chemin_onboarding_autorise(chemin: str) -> bool:
    return chemin.rstrip('/').startswith('/api/onboarding')


def _chemin_chatbot_autorise(chemin: str) -> bool:
    return chemin.rstrip('/').startswith('/api/chatbot')


def doit_bloquer_configuration_metier(request) -> tuple[bool, str, str]:
    if not controle_licence_actif():
        return False, '', ''

    methode = request.method.upper()
    if methode in METHODES_LECTURE:
        return False, '', ''

    chemin = request.path
    if chemin_exempt(chemin) or _chemin_onboarding_autorise(chemin) or _chemin_chatbot_autorise(chemin):
        return False, '', ''

    if chemin_setup_autorise(chemin, methode):
        return False, '', ''

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or user.is_superuser:
        return False, '', ''

    if onboarding_metier_autorise(user, request):
        return False, '', ''

    # Parcours d'onboarding terminé : on précise ce qui manque (entreprise ou profil)
    # plutôt que le message générique d'onboarding.
    status = build_onboarding_status(user, request)
    if status['onboarding_completed'] and status['welcome_seen']:
        if not status['company_completed']:
            return True, 'configuration_incomplete', _(
                'Action bloquée. Veuillez compléter les informations de votre entreprise avant de continuer.'
            )
        if not status['profile_completed']:
            return True, 'profil_incomplet', _(
                'Action bloquée. Veuillez compléter votre profil avant d\'effectuer cette opération.'
            )

    title, detail = message_blocage_onboarding(user, request)
    return True, 'onboarding_incomplet', detail
