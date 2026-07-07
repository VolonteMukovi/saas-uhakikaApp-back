"""Génération et validation des jetons de vérification d'e-mail."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from inscription.models import EmailVerificationToken

logger = logging.getLogger(__name__)


class ErreurVerificationEmail(Exception):
    def __init__(self, detail, *, code: str):
        self.detail = detail
        self.code = code
        super().__init__(detail)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _delai_renvoi_restant(dernier: EmailVerificationToken | None) -> int:
    if not dernier:
        return 0
    elapsed = (timezone.now() - dernier.cree_le).total_seconds()
    cooldown = int(getattr(settings, 'EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS', 60))
    return max(0, int(cooldown - elapsed))


def peut_renvoyer_verification(user) -> tuple[bool, int, str | None]:
    """Retourne (autorisé, secondes_restantes, code_erreur)."""
    if user.email_verifie:
        return False, 0, 'deja_verifie'

    now = timezone.now()
    dernier = (
        EmailVerificationToken.objects.filter(utilisateur=user)
        .order_by('-cree_le')
        .first()
    )
    restant = _delai_renvoi_restant(dernier)
    if restant > 0:
        return False, restant, 'cooldown'

    max_h = int(getattr(settings, 'EMAIL_VERIFICATION_RESEND_MAX_PER_HOUR', 5))
    count = EmailVerificationToken.objects.filter(
        utilisateur=user,
        cree_le__gte=now - timedelta(hours=1),
    ).count()
    if count >= max_h:
        return False, 0, 'quota_depasse'
    return True, 0, None


@transaction.atomic
def creer_jeton_verification(user, *, email_cible: str | None = None) -> tuple[str, EmailVerificationToken]:
    """Invalide les jetons actifs et crée un nouveau jeton. Retourne (token_clair, enregistrement)."""
    email = (email_cible or user.email or '').strip().lower()
    if not email:
        raise ErreurVerificationEmail(_('Adresse e-mail requise.'), code='email_manquant')

    EmailVerificationToken.objects.filter(
        utilisateur=user,
        utilise_le__isnull=True,
        invalide=False,
        expire_le__gt=timezone.now(),
    ).update(invalide=True)

    token_clair = secrets.token_urlsafe(32)
    hours = int(getattr(settings, 'EMAIL_VERIFICATION_TOKEN_HOURS', 24))
    expire_le = timezone.now() + timedelta(hours=hours)
    enregistrement = EmailVerificationToken.objects.create(
        utilisateur=user,
        token_hash=_hash_token(token_clair),
        email_cible=email,
        expire_le=expire_le,
    )
    return token_clair, enregistrement


def _frontend_path(path: str) -> str:
    path = path if path.startswith('/') else f'/{path}'
    locale = getattr(settings, 'FRONTEND_LOCALE_PREFIX', '').rstrip('/')
    return f'{locale}{path}' if locale else path


def build_frontend_url(path: str, *, query: str = '') -> str:
    """URL absolue vers une page frontend (locale incluse)."""
    base = getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')
    url = f'{base}{_frontend_path(path)}'
    if query:
        url = f'{url}?{query.lstrip("?")}'
    return url


def build_frontend_verification_url(token_clair: str) -> str:
    """Page frontend de confirmation avec le jeton dans la query string."""
    path = getattr(settings, 'FRONTEND_VERIFY_EMAIL_PATH', '/verify-email')
    encoded = quote(token_clair, safe='')
    return build_frontend_url(path, query=f'token={encoded}')


def build_verification_url(token_clair: str) -> str:
    """
    URL du bouton dans l'e-mail.
    En production : API GET → redirect frontend (préserve le token i18n).
    En local : lien frontend direct (évite 127.0.0.1 dans l'e-mail = signal spam).
    """
    encoded = quote(token_clair, safe='')
    via_api = getattr(settings, 'EMAIL_VERIFICATION_LINK_VIA_API', True)
    api_base = getattr(settings, 'PUBLIC_API_BASE_URL', '').rstrip('/')
    if via_api and api_base and not _url_est_locale(api_base):
        return f'{api_base}/api/inscription/confirmer-email/?token={encoded}'
    return build_frontend_verification_url(token_clair)


def _url_est_locale(url: str) -> bool:
    lower = (url or '').lower()
    return any(h in lower for h in ('localhost', '127.0.0.1', '0.0.0.0', '[::1]'))


@transaction.atomic
def confirmer_email_avec_jeton(token_clair: str):
    """
    Valide le jeton et active le compte.
    Retourne (user, code_message).
    """
    token_clair = (token_clair or '').strip()
    if not token_clair:
        raise ErreurVerificationEmail(
            _('Lien de vérification invalide.'),
            code='token_invalide',
        )

    token_hash = _hash_token(token_clair)
    jeton = (
        EmailVerificationToken.objects.select_for_update()
        .select_related('utilisateur')
        .filter(token_hash=token_hash)
        .first()
    )
    if not jeton:
        raise ErreurVerificationEmail(
            _('Lien de vérification invalide.'),
            code='token_invalide',
        )

    user = jeton.utilisateur
    if user.email_verifie:
        return user, 'deja_verifie'

    if jeton.utilise_le is not None or jeton.invalide:
        raise ErreurVerificationEmail(
            _('Ce lien de confirmation a déjà été utilisé.'),
            code='token_deja_utilise',
        )

    now = timezone.now()
    if jeton.expire_le < now:
        raise ErreurVerificationEmail(
            _('Ce lien de confirmation a expiré. Veuillez demander un nouveau message.'),
            code='token_expire',
        )

    user.email = jeton.email_cible or user.email
    user.email_verifie = True
    user.is_active = True
    user.save(update_fields=['email', 'email_verifie', 'is_active'])

    jeton.utilise_le = now
    jeton.save(update_fields=['utilise_le'])

    EmailVerificationToken.objects.filter(
        utilisateur=user,
        utilise_le__isnull=True,
        invalide=False,
    ).exclude(pk=jeton.pk).update(invalide=True)

    logger.info('Email vérifié pour user_id=%s', user.pk)
    return user, 'verifie'


@transaction.atomic
def modifier_email_en_attente(user, nouvel_email: str, *, password: str | None = None) -> str:
    """Change l'e-mail tant que le compte n'est pas vérifié. Retourne le nouveau jeton."""
    if user.email_verifie:
        raise ErreurVerificationEmail(
            _('Votre adresse e-mail est déjà confirmée.'),
            code='deja_verifie',
        )

    nouvel_email = (nouvel_email or '').strip().lower()
    if not nouvel_email:
        raise ErreurVerificationEmail(_('Nouvelle adresse e-mail requise.'), code='email_manquant')

    from django.contrib.auth import get_user_model
    User = get_user_model()
    if User.objects.filter(email__iexact=nouvel_email).exclude(pk=user.pk).exists():
        raise ErreurVerificationEmail(
            _('Un compte existe déjà avec cette adresse e-mail.'),
            code='email_indisponible',
        )

    if user.has_usable_password():
        if not password or not user.check_password(password):
            raise ErreurVerificationEmail(
                _('Mot de passe incorrect.'),
                code='mot_de_passe_invalide',
            )

    user.email = nouvel_email
    user.save(update_fields=['email'])
    token_clair, _jeton = creer_jeton_verification(user, email_cible=nouvel_email)
    return token_clair
