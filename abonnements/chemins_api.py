"""Chemins API exemptés / autorisés (partagé abonnements + inscription)."""
from __future__ import annotations

import re

METHODES_LECTURE = frozenset({'GET', 'HEAD', 'OPTIONS'})

CHEMINS_SETUP_AUTORISES = (
    re.compile(r'^/api/entreprises/\d+/?$'),
    re.compile(r'^/api/entreprises/\d+/config/?$'),
    re.compile(r'^/api/entreprises/\d+/config/document-appearance/[^/]+/?$'),
    re.compile(r'^/api/users/me/?$'),
    re.compile(r'^/api/users/\d+/?$'),
)


def chemin_setup_autorise(chemin: str, methode: str) -> bool:
    if methode not in ('PUT', 'PATCH'):
        return False
    chemin = chemin.rstrip('/') or '/'
    return any(p.match(chemin) for p in CHEMINS_SETUP_AUTORISES)
