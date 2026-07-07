"""Sélection du membership / entreprise principal pour un utilisateur."""
from __future__ import annotations

from users.models import Membership


def get_primary_membership(user, request=None):
    """
    Membership actif principal pour le contexte courant.

    Règles (parcours onboarding à une seule entreprise) :
    1. Contexte JWT explicite (request.current_membership)
    2. Un seul membership actif
    3. Plusieurs : admin avec entreprise configurée, sinon plus ancien admin
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    if request is not None:
        m = getattr(request, 'current_membership', None)
        if m is not None and m.user_id == user.pk and m.is_active:
            return m

    qs = (
        Membership.objects
        .filter(user=user, is_active=True)
        .select_related('entreprise', 'default_succursale')
        .order_by('id')
    )
    memberships = list(qs)
    if not memberships:
        return None
    if len(memberships) == 1:
        return memberships[0]

    admins = [m for m in memberships if m.role == 'admin']
    pool = admins or memberships

    configured = [
        m for m in pool
        if getattr(m.entreprise, 'configuration_complete', False)
    ]
    if len(configured) == 1:
        return configured[0]
    if configured:
        return min(configured, key=lambda m: m.id)

    return min(pool, key=lambda m: m.id)


def get_primary_entreprise(user, request=None):
    m = get_primary_membership(user, request)
    return m.entreprise if m else None
