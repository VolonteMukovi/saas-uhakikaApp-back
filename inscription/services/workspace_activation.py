"""Génération et validation des jetons d'activation finale de l'espace."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from inscription.models import WorkspaceActivationToken


class ErreurActivationEspace(Exception):
    def __init__(self, detail, *, code: str, title: str | None = None):
        self.detail = detail
        self.code = code
        self.title = title or _('Activation impossible')
        super().__init__(detail)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@transaction.atomic
def creer_jeton_activation_espace(user) -> tuple[str, WorkspaceActivationToken]:
    """Invalide les jetons actifs et crée un nouveau jeton d'activation."""
    WorkspaceActivationToken.objects.filter(
        utilisateur=user,
        utilise_le__isnull=True,
        invalide=False,
        expire_le__gt=timezone.now(),
    ).update(invalide=True)

    token_clair = secrets.token_urlsafe(32)
    jours = int(getattr(settings, 'WORKSPACE_ACTIVATION_TOKEN_DAYS', 7))
    expire_le = timezone.now() + timedelta(days=jours)
    enregistrement = WorkspaceActivationToken.objects.create(
        utilisateur=user,
        token_hash=_hash_token(token_clair),
        expire_le=expire_le,
    )
    return token_clair, enregistrement


def build_frontend_welcome_url(token_clair: str) -> str:
    from inscription.services.email_verification import build_frontend_url

    path = getattr(settings, 'FRONTEND_WELCOME_PATH', '/welcome')
    encoded = quote(token_clair, safe='')
    return build_frontend_url(path, query=f'token={encoded}')


def build_activation_espace_url(token_clair: str) -> str:
    """URL du bouton dans l'e-mail d'activation finale."""
    encoded = quote(token_clair, safe='')
    via_api = getattr(settings, 'WORKSPACE_ACTIVATION_LINK_VIA_API', True)
    api_base = getattr(settings, 'PUBLIC_API_BASE_URL', '').rstrip('/')
    if via_api and api_base and not _url_est_locale(api_base):
        return f'{api_base}/api/onboarding/activer-espace/?token={encoded}'
    return build_frontend_welcome_url(token_clair)


def _url_est_locale(url: str) -> bool:
    lower = (url or '').lower()
    return any(h in lower for h in ('localhost', '127.0.0.1', '0.0.0.0', '[::1]'))


@transaction.atomic
def activer_espace_avec_jeton(token_clair: str):
    """
    Valide le jeton d'activation finale.
    Retourne (user, code_message).
    """
    token_clair = (token_clair or '').strip()
    if not token_clair:
        raise ErreurActivationEspace(
            _('Lien d\'activation invalide.'),
            code='token_invalide',
        )

    token_hash = _hash_token(token_clair)
    jeton = (
        WorkspaceActivationToken.objects.select_for_update()
        .select_related('utilisateur')
        .filter(token_hash=token_hash)
        .first()
    )
    if not jeton:
        raise ErreurActivationEspace(
            _('Lien d\'activation invalide.'),
            code='token_invalide',
        )

    user = jeton.utilisateur
    if not getattr(user, 'onboarding_complete', False):
        raise ErreurActivationEspace(
            _('Veuillez terminer la configuration de votre espace avant d\'activer votre accès.'),
            code='onboarding_incomplet',
            title=_('Configuration incomplète'),
        )

    if user.workspace_activated and jeton.utilise_le is not None:
        return user, 'deja_active'

    if jeton.utilise_le is not None or jeton.invalide:
        raise ErreurActivationEspace(
            _('Ce lien d\'activation a déjà été utilisé.'),
            code='token_deja_utilise',
        )

    now = timezone.now()
    if jeton.expire_le < now:
        raise ErreurActivationEspace(
            _('Ce lien d\'activation a expiré. Connectez-vous pour demander un nouvel accès.'),
            code='token_expire',
        )

    user.workspace_activated = True
    user.save(update_fields=['workspace_activated'])

    jeton.utilise_le = now
    jeton.save(update_fields=['utilise_le'])

    WorkspaceActivationToken.objects.filter(
        utilisateur=user,
        utilise_le__isnull=True,
        invalide=False,
    ).exclude(pk=jeton.pk).update(invalide=True)

    return user, 'active'
