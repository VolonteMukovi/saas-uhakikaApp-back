"""Déclenchement unique de l'e-mail de bienvenue."""
from __future__ import annotations

import logging

from abonnements.services.limites import build_resume_limites
from abonnements.services.licence import build_etat_licence
from inscription.services.email_messaging import envoyer_email_bienvenue
from inscription.services.entreprise_saas import entreprise_est_configuree
from inscription.services.profil_saas import profil_est_complet

logger = logging.getLogger(__name__)


def peut_envoyer_bienvenue(user, request=None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if not getattr(user, 'email_verifie', False):
        return False
    if getattr(user, 'message_bienvenue_envoye', False):
        return False
    if not profil_est_complet(user):
        return False
    ent = user.get_entreprise(request)
    if not entreprise_est_configuree(ent):
        return False
    etat = build_etat_licence(ent.id) if ent else None
    if not etat or not etat.get('est_actif'):
        return False
    return True


def envoyer_bienvenue_si_eligible(user, request=None) -> bool:
    if not peut_envoyer_bienvenue(user, request):
        return False
    ent = user.get_entreprise(request)
    etat = build_etat_licence(ent.id)
    limites = build_resume_limites(ent.id, request)
    try:
        return envoyer_email_bienvenue(
            user,
            entreprise=ent,
            etat_licence=etat,
            limites_plan=limites,
        )
    except Exception:
        logger.exception('Échec envoi bienvenue user_id=%s', user.pk)
        return False
