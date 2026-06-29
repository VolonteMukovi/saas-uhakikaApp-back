"""
Quotas et fonctionnalités par plan (étape 4).
"""
from __future__ import annotations

from django.utils.translation import gettext as _

from abonnements.carte_fonctionnalites import (
    CHEMIN_SUCCURSALES,
    CHEMIN_UTILISATEURS,
    fonctionnalite_pour_requete,
)
from abonnements.controle_licence import controle_licence_actif, chemin_exempt
from abonnements.exceptions import FonctionnaliteNonAutorisee, LimiteQuotaAtteinte
from abonnements.services.licence import build_etat_licence, fonctionnalite_autorisee


def _etat(request, entreprise_id: int) -> dict:
    etat = getattr(request, 'etat_licence', None) if request else None
    if not etat or etat.get('abonnement_id') is None:
        etat = build_etat_licence(entreprise_id)
    if request is not None:
        request.etat_licence = etat
    return etat


def _lever_fonctionnalite(cle: str, etat: dict):
    raise FonctionnaliteNonAutorisee(
        detail=_(
            'Cette fonctionnalité (%(feature)s) n\'est pas disponible dans votre formule « %(plan)s ». '
            'Veuillez passer à une formule supérieure pour l\'utiliser.'
        ) % {'feature': cle, 'plan': etat.get('formule_nom') or etat.get('formule_code')},
    )


def _lever_quota(type_quota: str, max_val: int, actuel: int, etat: dict):
    raise LimiteQuotaAtteinte(
        detail=_(
            'Limite atteinte pour %(type)s : %(actuel)s / %(max)s sur la formule « %(plan)s ». '
            'Passez à une formule supérieure pour en ajouter.'
        ) % {
            'type': type_quota,
            'actuel': actuel,
            'max': max_val,
            'plan': etat.get('formule_nom') or etat.get('formule_code'),
        },
        type_quota=type_quota,
        maximum=max_val,
        actuel=actuel,
    )


def compter_utilisateurs_actifs(entreprise_id: int) -> int:
    from users.models import Membership
    return Membership.objects.filter(entreprise_id=entreprise_id, is_active=True).count()


def compter_succursales_actives(entreprise_id: int) -> int:
    from stock.models import Succursale
    return Succursale.objects.filter(entreprise_id=entreprise_id, is_active=True).count()


def build_resume_limites(entreprise_id: int, request=None) -> dict:
    etat = _etat(request, entreprise_id)
    limites = etat.get('limites') or {}
    utilisateurs = compter_utilisateurs_actifs(entreprise_id)
    succursales = compter_succursales_actives(entreprise_id)
    max_u = limites.get('utilisateurs_max')
    max_s = limites.get('succursales_max')

    return {
        'formule_code': etat.get('formule_code'),
        'formule_nom': etat.get('formule_nom'),
        'est_essai': etat.get('est_essai', False),
        'fonctionnalites': etat.get('fonctionnalites') or {},
        'utilisateurs': {
            'actuels': utilisateurs,
            'maximum': max_u,
            'peut_ajouter': max_u is None or utilisateurs < max_u,
        },
        'succursales': {
            'actuelles': succursales,
            'maximum': max_s,
            'peut_ajouter': (
                fonctionnalite_autorisee(entreprise_id, 'multi_succursales')
                and (max_s is None or succursales < max_s)
            ) if not etat.get('est_essai') else (max_s is None or succursales < max_s),
        },
    }


def verifier_fonctionnalite_active(entreprise_id: int, cle: str, request=None):
    if not controle_licence_actif():
        return
    etat = _etat(request, entreprise_id)
    if not etat.get('est_actif'):
        return  # étape 3 gère l'expiration
    if not fonctionnalite_autorisee(entreprise_id, cle):
        _lever_fonctionnalite(cle, etat)


def verifier_creation_utilisateur(entreprise_id: int, request=None):
    etat = _etat(request, entreprise_id)
    max_u = (etat.get('limites') or {}).get('utilisateurs_max')
    if max_u is None:
        return
    actuel = compter_utilisateurs_actifs(entreprise_id)
    if actuel >= max_u:
        _lever_quota('utilisateurs', max_u, actuel, etat)


def verifier_creation_succursale(entreprise_id: int, request=None):
    etat = _etat(request, entreprise_id)
    if not etat.get('est_essai') and not fonctionnalite_autorisee(entreprise_id, 'multi_succursales'):
        actuel = compter_succursales_actives(entreprise_id)
        if actuel >= 1:
            _lever_fonctionnalite('multi_succursales', etat)
    max_s = (etat.get('limites') or {}).get('succursales_max')
    if max_s is not None:
        actuel = compter_succursales_actives(entreprise_id)
        if actuel >= max_s:
            _lever_quota('succursales', max_s, actuel, etat)


def verifier_vente_sortie(entreprise_id: int, statut: str, request=None):
    verifier_fonctionnalite_active(entreprise_id, 'vente_comptant', request)
    if statut == 'EN_CREDIT':
        verifier_fonctionnalite_active(entreprise_id, 'vente_credit', request)


def doit_bloquer_fonctionnalite_plan(request) -> tuple[bool, str | None, dict | None]:
    """
    Retourne (bloquer, cle_fonctionnalite, etat_licence).
    """
    if not controle_licence_actif():
        return False, None, None

    methode = request.method.upper()
    chemin = request.path

    if chemin_exempt(chemin):
        return False, None, None

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or user.is_superuser:
        return False, None, None

    eid = getattr(request, 'tenant_id', None) or user.get_entreprise_id(request)
    if not eid:
        return False, None, None

    etat = _etat(request, eid)
    if not etat.get('est_actif'):
        return False, None, etat  # étape 3 bloque déjà les écritures

    # Quotas utilisateurs / succursales (POST)
    if methode == 'POST':
        if CHEMIN_UTILISATEURS.match(chemin.rstrip('/') or '/'):
            try:
                verifier_creation_utilisateur(eid, request)
            except (FonctionnaliteNonAutorisee, LimiteQuotaAtteinte):
                raise
            return False, None, etat
        if CHEMIN_SUCCURSALES.match(chemin.rstrip('/') or '/'):
            try:
                verifier_creation_succursale(eid, request)
            except (FonctionnaliteNonAutorisee, LimiteQuotaAtteinte):
                raise
            return False, None, etat

    cle, _ = fonctionnalite_pour_requete(chemin, methode)
    if not cle:
        return False, None, etat

    if not fonctionnalite_autorisee(eid, cle):
        return True, cle, etat

    return False, None, etat
