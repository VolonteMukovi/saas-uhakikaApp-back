"""
État onboarding unifié pour le frontend (next_step, guards, reprise interrompue).
"""
from __future__ import annotations

from django.conf import settings
from django.utils.translation import gettext as _

from inscription.services.entreprise_saas import entreprise_est_configuree
from inscription.services.profil_saas import profil_est_complet

NEXT_VERIFY_EMAIL = 'verify-email'
NEXT_PROFILE = 'profile'
NEXT_COMPANY = 'company'
NEXT_REVIEW = 'review'
NEXT_ACTIVATION = 'activation'
NEXT_WELCOME = 'welcome'
NEXT_DASHBOARD = 'dashboard'

VALID_NEXT_STEPS = frozenset({
    NEXT_VERIFY_EMAIL,
    NEXT_PROFILE,
    NEXT_COMPANY,
    NEXT_REVIEW,
    NEXT_ACTIVATION,
    NEXT_WELCOME,
    NEXT_DASHBOARD,
})


def _frontend_path(key: str, default: str) -> str:
    locale = getattr(settings, 'FRONTEND_LOCALE_PREFIX', '').rstrip('/')
    path = getattr(settings, key, default)
    path = path if path.startswith('/') else f'/{path}'
    return f'{locale}{path}' if locale else path


def resoudre_next_step(user, request=None) -> str:
    if not user or not getattr(user, 'is_authenticated', False):
        return NEXT_VERIFY_EMAIL

    if user.is_superuser:
        return NEXT_DASHBOARD

    if not getattr(user, 'email_verifie', False):
        return NEXT_VERIFY_EMAIL

    profile_ok = profil_est_complet(user)
    ent = user.get_entreprise(request) if hasattr(user, 'get_entreprise') else None
    company_ok = entreprise_est_configuree(ent)

    if not profile_ok:
        return NEXT_PROFILE
    if not company_ok:
        return NEXT_COMPANY
    if not getattr(user, 'onboarding_complete', False):
        return NEXT_REVIEW
    if not getattr(user, 'workspace_activated', False):
        return NEXT_ACTIVATION
    if not getattr(user, 'welcome_seen', False):
        return NEXT_WELCOME
    return NEXT_DASHBOARD


def chemin_redirection_pour_etape(next_step: str) -> str:
    mapping = {
        NEXT_VERIFY_EMAIL: _frontend_path('FRONTEND_VERIFY_EMAIL_PATH', '/verify-email'),
        NEXT_PROFILE: _frontend_path('FRONTEND_ONBOARDING_PROFILE_PATH', '/onboarding/profile'),
        NEXT_COMPANY: _frontend_path('FRONTEND_ONBOARDING_COMPANY_PATH', '/onboarding/company'),
        NEXT_REVIEW: _frontend_path('FRONTEND_ONBOARDING_REVIEW_PATH', '/onboarding/review'),
        NEXT_ACTIVATION: _frontend_path('FRONTEND_ONBOARDING_ACTIVATION_PATH', '/onboarding/activation'),
        NEXT_WELCOME: _frontend_path('FRONTEND_WELCOME_PATH', '/welcome'),
        NEXT_DASHBOARD: _frontend_path('FRONTEND_DASHBOARD_PATH', '/dashboard'),
    }
    return mapping.get(next_step, mapping[NEXT_PROFILE])


def build_onboarding_status(user, request=None) -> dict:
    """Réponse GET /api/onboarding/status/."""
    ent = user.get_entreprise(request) if (user and user.is_authenticated) else None
    profile_ok = profil_est_complet(user) if user and user.is_authenticated else False
    company_ok = entreprise_est_configuree(ent)
    email_ok = bool(user and user.is_authenticated and getattr(user, 'email_verifie', False))
    onboarding_ok = bool(user and getattr(user, 'onboarding_complete', False))
    workspace_ok = bool(user and getattr(user, 'workspace_activated', False))
    welcome_ok = bool(user and getattr(user, 'welcome_seen', False))
    next_step = resoudre_next_step(user, request)

    return {
        'email_verified': email_ok,
        'profile_completed': profile_ok,
        'company_completed': company_ok,
        'onboarding_completed': onboarding_ok,
        'welcome_seen': welcome_ok,
        'workspace_activated': workspace_ok,
        'email_activation_sent': bool(user and getattr(user, 'email_activation_envoye', False)),
        'next_step': next_step,
        'redirection': chemin_redirection_pour_etape(next_step),
        'acces_dashboard': (
            email_ok and onboarding_ok and workspace_ok and welcome_ok
        ),
    }


def onboarding_metier_autorise(user, request=None) -> bool:
    """True si l'utilisateur peut accéder aux opérations métier (ventes, stock, etc.)."""
    if not user or not user.is_authenticated or user.is_superuser:
        return bool(user and user.is_authenticated)
    status = build_onboarding_status(user, request)
    if not status['onboarding_completed'] or not status['welcome_seen']:
        return False
    if not status['profile_completed'] or not status['company_completed']:
        return False
    return True


def message_blocage_onboarding(user, request=None) -> tuple[str, str]:
    """Retourne (title, detail) pour une réponse 403."""
    next_step = resoudre_next_step(user, request)
    if next_step == NEXT_VERIFY_EMAIL:
        return (
            _('Adresse e-mail non confirmée'),
            _('Confirmez votre adresse e-mail pour poursuivre la configuration de votre espace.'),
        )
    if next_step == NEXT_PROFILE:
        return (
            _('Profil incomplet'),
            _('Veuillez compléter votre profil avant d\'accéder à cette fonctionnalité.'),
        )
    if next_step == NEXT_COMPANY:
        return (
            _('Configuration entreprise incomplète'),
            _('Veuillez renseigner les informations de votre entreprise pour continuer.'),
        )
    if next_step == NEXT_REVIEW:
        return (
            _('Onboarding non finalisé'),
            _('Vérifiez et confirmez votre configuration pour activer votre espace.'),
        )
    if next_step == NEXT_ACTIVATION:
        return (
            _('Activation en attente'),
            _('Consultez votre boîte e-mail et cliquez sur le lien pour activer votre espace UHAKIKAAPP.'),
        )
    if next_step == NEXT_WELCOME:
        return (
            _('Bienvenue en attente'),
            _('Terminez l\'accueil à votre espace avant d\'utiliser le tableau de bord.'),
        )
    return (
        _('Accès restreint'),
        _('Veuillez terminer la configuration de votre compte.'),
    )
