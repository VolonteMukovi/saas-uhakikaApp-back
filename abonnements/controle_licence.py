"""
Règles de contrôle d'accès selon la licence (étape 3 SaaS).

- Lecture (GET/HEAD/OPTIONS) : toujours autorisée si authentifié.
- Écriture (POST/PUT/PATCH/DELETE) : bloquée si licence inactive / expirée.
- Chemins exemptés : auth, inscription, abonnement, création entreprise.
"""
from __future__ import annotations

import re

from django.conf import settings
from django.utils.translation import gettext as _

from abonnements.chemins_api import chemin_setup_autorise
from abonnements.services.licence import build_etat_licence

METHODES_LECTURE = frozenset({'GET', 'HEAD', 'OPTIONS'})

# Préfixes toujours exemptés (auth, onboarding, catalogue abonnements).
CHEMINS_EXEMPTES_PREFIXES = (
    '/api/auth/',
    '/api/inscription/',
    '/admin/',
    '/swagger',
    '/redoc/',
    '/api/abonnements/formules',
    '/api/abonnements/mon-abonnement',
    '/api/abonnements/mes-limites',
    '/api/abonnements/demander',
    '/api/abonnements/installation-privee',
    '/api/abonnements/paiements/',
    '/api/plateforme/',
    '/api/i18n-test/',
)

# GET autorisés même sans licence (consultation profil / entreprise).
CHEMINS_LECTURE_EXPLICITE = (
    re.compile(r'^/api/users/me/?$'),
    re.compile(r'^/api/users/\d+/?$'),  # profil propre (contrôle rôle dans la vue)
    re.compile(r'^/api/entreprises/?$'),
    re.compile(r'^/api/entreprises/\d+/?$'),
    re.compile(r'^/api/entreprises/my_entreprise/?$'),
)


def controle_licence_actif() -> bool:
    return bool(getattr(settings, 'LICENCE_CONTROLE_ACTIF', True))


def chemin_exempt(chemin: str) -> bool:
    chemin = chemin.rstrip('/') or '/'
    for prefix in CHEMINS_EXEMPTES_PREFIXES:
        if chemin.startswith(prefix.rstrip('/')):
            return True
    return False


def lecture_entreprise_autorisee(chemin: str, methode: str) -> bool:
    if methode not in METHODES_LECTURE:
        return False
    for pattern in CHEMINS_LECTURE_EXPLICITE:
        if pattern.match(chemin.rstrip('/') or '/'):
            return True
    return False


def creation_entreprise_autorisee(chemin: str, methode: str, user) -> bool:
    """Autorise POST /api/entreprises/ si l'utilisateur n'a pas encore d'entreprise."""
    if methode != 'POST':
        return False
    if not chemin.rstrip('/').endswith('/api/entreprises'):
        return False
    if not user or not user.is_authenticated or user.is_superuser:
        return False
    return user.memberships.filter(is_active=True).count() == 0


def doit_bloquer_ecriture(request) -> tuple[bool, dict | None]:
    """
    Retourne (bloquer, etat_licence).
    False = laisser passer.
    """
    if not controle_licence_actif():
        return False, None

    methode = request.method.upper()
    if methode in METHODES_LECTURE:
        return False, None

    chemin = request.path

    if chemin_exempt(chemin):
        return False, None

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False, None

    if user.is_superuser:
        return False, None

    if creation_entreprise_autorisee(chemin, methode, user):
        return False, None

    if chemin_setup_autorise(chemin, methode):
        return False, None

    if lecture_entreprise_autorisee(chemin, methode):
        return False, None

    eid = getattr(request, 'tenant_id', None) or user.get_entreprise_id(request)
    if not eid:
        # Pas d'entreprise : seules inscription + création entreprise (déjà exemptées).
        return False, None

    etat = getattr(request, 'etat_licence', None) or build_etat_licence(eid)
    request.etat_licence = etat

    if etat.get('est_actif'):
        return False, etat

    return True, etat


def message_blocage_licence(etat: dict | None) -> str:
    if etat and etat.get('message'):
        return str(etat['message'])
    return _(
        'Votre abonnement a expiré ou est inactif. '
        'Veuillez renouveler votre formule pour continuer à utiliser cette fonctionnalité.'
    )
