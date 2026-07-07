"""Consolidation automatique des entreprises en double (onboarding)."""
from __future__ import annotations

from django.db import transaction

from inscription.services.entreprise_saas import (
    entreprise_contient_donnees_metier,
    entreprise_est_configuree,
)
from stock.models import Entreprise
from users.models import Membership
from users.services.membership_context import get_primary_membership


def lister_doublons_utilisateur(user) -> list[dict]:
    memberships = list(
        Membership.objects
        .filter(user=user, is_active=True, role='admin')
        .select_related('entreprise')
        .order_by('id')
    )
    if len(memberships) <= 1:
        return []

    primary = get_primary_membership(user)
    return [
        {
            'membership_id': m.id,
            'entreprise_id': m.entreprise_id,
            'nom': m.entreprise.nom,
            'configuration_complete': bool(m.entreprise.configuration_complete),
            'configuree_metier': entreprise_est_configuree(m.entreprise),
            'donnees_metier': entreprise_contient_donnees_metier(m.entreprise),
            'est_principale': bool(primary and primary.id == m.id),
            'provisoire': not entreprise_est_configuree(m.entreprise),
        }
        for m in memberships
    ]


@transaction.atomic
def consolider_entreprises_utilisateur(user) -> int:
    """
    Supprime les entreprises provisoires vides en double.
    Conserve l'entreprise principale (configurée ou la plus ancienne).
    """
    memberships = list(
        Membership.objects
        .filter(user=user, is_active=True, role='admin')
        .select_related('entreprise')
        .order_by('id')
    )
    if len(memberships) <= 1:
        return 0

    primary = get_primary_membership(user)
    if not primary:
        return 0

    supprimees = 0
    for m in memberships:
        if m.id == primary.id:
            continue
        ent = m.entreprise
        if entreprise_contient_donnees_metier(ent):
            continue
        if entreprise_est_configuree(ent) and ent.configuration_complete:
            continue
        Membership.objects.filter(pk=m.pk).delete()
        if not Membership.objects.filter(entreprise_id=ent.id).exists():
            Entreprise.objects.filter(pk=ent.id).delete()
            supprimees += 1
    return supprimees
