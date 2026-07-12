"""Vérification des droits par domaine métier."""
from __future__ import annotations

from dataclasses import dataclass

from django.utils.translation import gettext as _

from chatbot.context import ChatbotContext


@dataclass
class PermissionResult:
    allowed: bool
    title: str | None = None
    detail: str | None = None


CONVERSATIONAL_INTENTS = frozenset({
    'salutation',
    'remerciement',
    'compliment',
    'comprehension',
    'petite_conversation',
    'contexte_utilisateur',
    'uhakika_info',
    'hors_sujet',
    'hors_sujet_sensible',
    'question_interdite',
})

DOMAIN_FEATURE_KEYS = {
    'stock': 'stock',
    'caisse': 'caisse',
    'ventes': 'vente_comptant',
    'dettes': 'dettes',
    'clients': 'clients',
    'rapports': 'rapports_simples',
    'abonnement': None,
    'aide': None,
    'platform': None,
    'security_bypass': None,
}


def check_domain_permission(ctx: ChatbotContext, intent: str) -> PermissionResult:
    if intent == 'security_bypass':
        return PermissionResult(
            allowed=False,
            title=_('Demande non autorisée'),
            detail=_('Je ne peux pas contourner les règles de sécurité de l’application.'),
        )

    if intent in CONVERSATIONAL_INTENTS:
        if not ctx.user.is_authenticated:
            return _auth_required()
        return PermissionResult(allowed=True)

    if intent == 'aide':
        if not ctx.user.is_authenticated:
            return _auth_required()
        return PermissionResult(allowed=True)

    if intent == 'platform':
        if not ctx.is_superadmin:
            return PermissionResult(
                allowed=False,
                title=_('Accès refusé'),
                detail=_('Ces statistiques plateforme sont réservées au super administrateur.'),
            )
        return PermissionResult(allowed=True)

    if intent in ('stock', 'caisse', 'ventes', 'dettes', 'clients', 'rapports', 'abonnement'):
        if not ctx.user.is_authenticated:
            return _auth_required()
        if ctx.is_superadmin and ctx.tenant_id is None:
            return PermissionResult(
                allowed=False,
                title=_('Contexte entreprise requis'),
                detail=_('Veuillez sélectionner une entreprise avant de consulter ses données métier.'),
            )
        if not ctx.tenant_id:
            return PermissionResult(
                allowed=False,
                title=_('Contexte entreprise manquant'),
                detail=_('Aucune entreprise active n’est associée à votre session.'),
            )
        if not ctx.chatbot_plan_ok:
            return PermissionResult(
                allowed=False,
                title=_('Fonctionnalité non incluse'),
                detail=_('L’assistant intelligent n’est pas inclus dans votre formule d’abonnement.'),
            )
        if not ctx.operations_metier_ok:
            return PermissionResult(
                allowed=False,
                title=_('Configuration incomplète'),
                detail=_('Terminez l’onboarding et l’activation de votre espace pour utiliser l’assistant métier.'),
            )
        if not (ctx.is_admin or ctx.is_agent):
            return PermissionResult(
                allowed=False,
                title=_('Accès refusé'),
                detail=_('Votre compte ne dispose pas des droits nécessaires pour consulter ces informations.'),
            )

        feature = DOMAIN_FEATURE_KEYS.get(intent)
        if feature and ctx.tenant_id:
            from abonnements.services.licence import fonctionnalite_autorisee

            if not fonctionnalite_autorisee(ctx.tenant_id, feature):
                labels = {
                    'stock': _('le stock'),
                    'caisse': _('la caisse'),
                    'vente_comptant': _('les ventes'),
                    'dettes': _('les dettes'),
                    'clients': _('les clients'),
                    'rapports_simples': _('les rapports'),
                }
                label = labels.get(feature, _('cette fonctionnalité'))
                return PermissionResult(
                    allowed=False,
                    title=_('Accès refusé'),
                    detail=_('Vous n’avez pas l’autorisation de consulter les informations de %(module)s.') % {
                        'module': label,
                    },
                )

        return PermissionResult(allowed=True)

    return PermissionResult(allowed=True)


def _auth_required() -> PermissionResult:
    return PermissionResult(
        allowed=False,
        title=_('Authentification requise'),
        detail=_('Vous devez être connecté pour utiliser l’assistant UHAKIKAAPP.'),
    )
