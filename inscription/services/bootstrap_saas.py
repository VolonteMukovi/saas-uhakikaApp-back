"""
Bootstrap post-authentification : entreprise minimale + essai Découverte Pro (60 jours).

Garantit qu'un utilisateur authentifié sans contexte métier n'atteint jamais
le dashboard dans un état sans entreprise, sans rôle ni licence.
"""
from __future__ import annotations

from django.utils.translation import gettext as _

from abonnements.models import AbonnementEntreprise, FormuleAbonnement
from abonnements.services.licence import demarrer_essai_gratuit, get_abonnement_courant
from inscription.services.entreprise_saas import creer_entreprise_minimale
from users.models import Membership


def _nom_entreprise_par_defaut(user) -> str:
    full = (user.get_full_name() or '').strip()
    if full:
        return f'{full} - Entreprise'
    if user.email:
        local = user.email.split('@')[0].replace('.', ' ').replace('_', ' ').strip()
        if local:
            return local.title()
    return f'Espace {user.username}'


def assurer_contexte_initial_utilisateur(
    user,
    *,
    nom_entreprise: str | None = None,
    pays: str = '',
) -> dict:
    """
    Crée ou complète le contexte SaaS minimal si nécessaire. Idempotent.

    Retourne un dict avec bootstrap_effectue (bool) et détails métier.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return {'bootstrap_effectue': False, 'raison': 'non_authentifie'}

    if user.is_superuser and not Membership.objects.filter(user=user, is_active=True).exists():
        return {'bootstrap_effectue': False, 'raison': 'superadmin_sans_contexte'}

    membership = (
        Membership.objects
        .filter(user=user, is_active=True)
        .select_related('entreprise')
        .order_by('entreprise_id', 'id')
        .first()
    )

    if membership:
        abo = get_abonnement_courant(membership.entreprise_id)
        if abo:
            return {
                'bootstrap_effectue': False,
                'raison': 'contexte_existant',
                'entreprise_id': membership.entreprise_id,
                'entreprise_nom': membership.entreprise.nom,
                'abonnement_id': abo.id,
                'statut_licence': abo.statut,
            }
        abo = demarrer_essai_gratuit(membership.entreprise, user=user)
        return {
            'bootstrap_effectue': True,
            'type': 'essai_active',
            'entreprise_id': membership.entreprise_id,
            'entreprise_nom': membership.entreprise.nom,
            'abonnement_id': abo.id,
            'statut_licence': abo.statut,
            'message': _('Essai gratuit Découverte Pro activé pour 60 jours.'),
        }

    result = creer_entreprise_minimale(
        user,
        nom=(nom_entreprise or _nom_entreprise_par_defaut(user)).strip(),
        pays=pays,
        email_entreprise=user.email or '',
        formule_code=FormuleAbonnement.CODE_ESSAI,
        periode=AbonnementEntreprise.PERIODE_ESSAI,
        source_activation='essai_gratuit',
    )
    return {
        'bootstrap_effectue': True,
        'type': 'contexte_cree',
        **result,
        'message': result.get('message')
        or _('Espace UHAKIKAAPP configuré. Essai gratuit Découverte Pro activé pour 60 jours.'),
    }
