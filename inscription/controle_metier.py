"""Contrôle configuration entreprise / profil avant opérations métier."""
from __future__ import annotations

from django.utils.translation import gettext as _

from abonnements.chemins_api import METHODES_LECTURE, chemin_setup_autorise
from abonnements.controle_licence import chemin_exempt, controle_licence_actif
from inscription.services.entreprise_saas import entreprise_est_configuree
from inscription.services.profil_saas import profil_est_complet


def doit_bloquer_configuration_metier(request) -> tuple[bool, str, str]:
    if not controle_licence_actif():
        return False, '', ''

    methode = request.method.upper()
    if methode in METHODES_LECTURE:
        return False, '', ''

    if chemin_exempt(request.path):
        return False, '', ''

    if chemin_setup_autorise(request.path, methode):
        return False, '', ''

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or user.is_superuser:
        return False, '', ''

    eid = getattr(request, 'tenant_id', None) or user.get_entreprise_id(request)
    if not eid:
        return False, '', ''

    ent = user.get_entreprise(request)
    if ent and not entreprise_est_configuree(ent):
        return True, 'configuration_incomplete', _(
            'Action bloquée. Veuillez compléter les informations de votre entreprise avant de continuer.'
        )

    if not profil_est_complet(user):
        return True, 'profil_incomplet', _(
            'Action bloquée. Veuillez compléter votre profil avant d\'effectuer cette opération.'
        )

    return False, '', ''
