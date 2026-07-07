"""
Vérification du jeton Google ID et connexion / inscription utilisateur.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext as _
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from inscription.models import ProfilConnexionGoogle

User = get_user_model()
logger = logging.getLogger(__name__)


class ErreurConnexionGoogle(Exception):
    """Erreur métier lors de la connexion Google."""

    def __init__(self, message, code='google_auth_error', hint=None):
        super().__init__(message)
        self.code = code
        self.hint = hint


def _client_ids_autorises() -> list[str]:
    raw = getattr(settings, 'GOOGLE_OAUTH_CLIENT_IDS', None) or []
    if isinstance(raw, str):
        return [x.strip() for x in raw.split(',') if x.strip()]
    return [x for x in raw if x]


def _normaliser_jeton_google(raw: str) -> str:
    token = (raw or '').strip()
    if token.lower().startswith('bearer '):
        token = token[7:].strip()
    return token


def _est_jwt(val: str) -> bool:
    return len(val.split('.')) == 3


def _decoder_payload_jwt_sans_verif(token: str) -> dict:
    parts = token.split('.')
    if len(parts) != 3:
        return {}
    try:
        padding = parts[1] + '=' * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(padding))
    except (ValueError, json.JSONDecodeError):
        return {}


def _audiences_du_payload(payload: dict) -> list[str]:
    aud = payload.get('aud')
    if isinstance(aud, str):
        return [aud]
    if isinstance(aud, (list, tuple)):
        return [str(x) for x in aud if x]
    azp = payload.get('azp')
    return [str(azp)] if azp else []


def _clock_skew_seconds() -> int:
    return int(getattr(settings, 'GOOGLE_OAUTH_CLOCK_SKEW_SECONDS', 300))


def _hint_horloge(token_hint: dict) -> dict:
    now = int(time.time())
    exp = token_hint.get('exp')
    iat = token_hint.get('iat')
    hint = {
        'server_unix': now,
        'token_exp': exp,
        'token_iat': iat,
    }
    if isinstance(exp, int):
        hint['seconds_past_exp'] = now - exp
    if isinstance(iat, int):
        hint['seconds_before_iat'] = iat - now
    return hint


def _est_erreur_horloge(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return 'expired' in msg or 'too early' in msg


def _verifier_via_tokeninfo_google(token: str, client_ids: list[str]) -> dict | None:
    """
    Fallback : Google valide exp/iat avec son horloge (utile si l'horloge Windows du serveur est décalée).
    """
    url = 'https://oauth2.googleapis.com/tokeninfo?id_token=' + urllib.parse.quote(token, safe='')
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors='replace') if exc.fp else ''
        logger.warning('Tokeninfo Google HTTP %s: %s', exc.code, body[:500])
        return None
    except Exception as exc:
        logger.warning('Tokeninfo Google indisponible: %s', exc)
        return None

    if data.get('error') or not data.get('sub'):
        return None

    aud = str(data.get('aud') or '')
    if aud not in client_ids:
        raise ErreurConnexionGoogle(
            _(
                'Le Client ID Google du frontend ne correspond pas au serveur. '
                'Le jeton a été émis pour « %(aud)s ». '
                'Utilisez GET /api/inscription/google/config/ pour initialiser le bouton Google.'
            )
            % {'aud': aud},
            code='audience_mismatch',
            hint={
                'token_audience': aud,
                'server_client_ids': client_ids,
            },
        )

    email_verified = str(data.get('email_verified', '')).lower() in ('true', '1')
    return {
        'sub': data.get('sub'),
        'email': data.get('email'),
        'email_verified': email_verified,
        'given_name': data.get('given_name') or '',
        'family_name': data.get('family_name') or '',
        'picture': data.get('picture') or '',
        'iss': data.get('iss') or '',
        'aud': aud,
    }


def _valider_claims_google(payload: dict, client_ids: list[str]) -> dict:
    audiences = _audiences_du_payload(payload)
    if not any(a in client_ids for a in audiences):
        aud_label = audiences[0] if audiences else '?'
        raise ErreurConnexionGoogle(
            _(
                'Client ID Google non autorisé sur ce serveur (audience: %(aud)s). '
                'Alignez le client_id du frontend avec GET /api/inscription/google/config/.'
            )
            % {'aud': aud_label},
            code='audience_mismatch',
            hint={
                'token_audience': audiences[0] if audiences else None,
                'server_client_ids': client_ids,
            },
        )

    iss = payload.get('iss', '')
    if iss not in ('accounts.google.com', 'https://accounts.google.com'):
        raise ErreurConnexionGoogle(_('Émetteur Google non reconnu.'), code='invalid_issuer')

    if not payload.get('email_verified', False):
        raise ErreurConnexionGoogle(
            _('L\'adresse e-mail Google n\'est pas vérifiée.'),
            code='email_not_verified',
        )

    if not payload.get('sub'):
        raise ErreurConnexionGoogle(_('Identifiant Google manquant.'), code='invalid_token')

    return payload


def _message_erreur_verification(exc: ValueError, token_hint: dict, client_ids: list[str]) -> ErreurConnexionGoogle:
    msg = str(exc).lower()
    audiences = _audiences_du_payload(token_hint)
    clock_hint = _hint_horloge(token_hint)

    if _est_erreur_horloge(exc):
        skew = clock_hint.get('seconds_past_exp')
        if isinstance(skew, int) and skew > 3600:
            return ErreurConnexionGoogle(
                _(
                    'Horloge du serveur probablement incorrecte (décalage d\'environ %(heures)d h par rapport au jeton Google). '
                    'Synchronisez la date/heure Windows, puis réessayez.'
                )
                % {'heures': max(1, skew // 3600)},
                code='server_clock_skew',
                hint=clock_hint,
            )
        if 'too early' in msg:
            return ErreurConnexionGoogle(
                _(
                    'Jeton Google rejeté car l\'horloge du serveur est en retard. '
                    'Synchronisez la date/heure Windows, puis réessayez.'
                ),
                code='server_clock_skew',
                hint=clock_hint,
            )
        return ErreurConnexionGoogle(
            _(
                'Jeton Google expiré ou déjà utilisé. Cliquez à nouveau sur « Continuer avec Google » '
                'sans réutiliser un ancien jeton en cache.'
            ),
            code='token_expired',
            hint=clock_hint,
        )

    if audiences and client_ids and not any(a in client_ids for a in audiences):
        return ErreurConnexionGoogle(
            _(
                'Le Client ID Google du frontend ne correspond pas au serveur. '
                'Le jeton a été émis pour « %(aud)s ». '
                'Utilisez GET /api/inscription/google/config/ pour initialiser le bouton Google.'
            )
            % {'aud': audiences[0]},
            code='audience_mismatch',
            hint={
                'token_audience': audiences[0],
                'server_client_ids': client_ids,
            },
        )

    if not _est_jwt(str(exc)) and ('signature' in msg or 'verify' in msg):
        return ErreurConnexionGoogle(
            _(
                'Jeton Google non reconnu. Envoyez le JWT « credential » renvoyé par '
                'Google Identity Services (bouton GIS), pas un access_token OAuth.'
            ),
            code='invalid_token',
        )

    logger.warning(
        'Échec vérification jeton Google: %s (aud=%s, iss=%s)',
        exc,
        audiences,
        token_hint.get('iss'),
    )
    return ErreurConnexionGoogle(
        _(
            'Jeton Google invalide. Vérifiez que le frontend envoie response.credential '
            'immédiatement après la connexion Google (GIS), pas un ancien jeton ni un access_token.'
        ),
        code='invalid_token',
    )


def verifier_id_token_google(id_token_str: str) -> dict:
    """
    Valide le jeton ID émis par Google Sign-In (GIS).
    Vérifie la signature, l'expiration et l'audience (client_id).
    """
    client_ids = _client_ids_autorises()
    if not client_ids:
        raise ErreurConnexionGoogle(
            _('La connexion Google n\'est pas configurée sur le serveur.'),
            code='google_not_configured',
        )

    token = _normaliser_jeton_google(id_token_str)
    if not token:
        raise ErreurConnexionGoogle(
            _('Le jeton Google est vide.'),
            code='invalid_token_format',
        )

    if not _est_jwt(token):
        raise ErreurConnexionGoogle(
            _(
                'Format de jeton invalide : un JWT Google (3 segments séparés par des points) '
                'est attendu dans « credential » ou « id_token ».'
            ),
            code='invalid_token_format',
        )

    token_hint = _decoder_payload_jwt_sans_verif(token)
    clock_skew = _clock_skew_seconds()
    payload = None
    verify_error = None

    try:
        request = google_requests.Request()
        payload = id_token.verify_oauth2_token(
            token,
            request,
            audience=None,
            clock_skew_in_seconds=clock_skew,
        )
    except ErreurConnexionGoogle:
        raise
    except ValueError as exc:
        verify_error = exc
        if _est_erreur_horloge(exc):
            logger.warning(
                'Vérification locale Google échouée (horloge): %s | hint=%s',
                exc,
                _hint_horloge(token_hint),
            )
            horloge_hint = _hint_horloge(token_hint)
            # Réessai avec tolérance élargie si l'horloge Windows est en retard.
            before_iat = horloge_hint.get('seconds_before_iat')
            if payload is None and isinstance(before_iat, int) and before_iat > clock_skew:
                try:
                    request = google_requests.Request()
                    payload = id_token.verify_oauth2_token(
                        token,
                        request,
                        audience=None,
                        clock_skew_in_seconds=before_iat + 120,
                    )
                    logger.info(
                        'Jeton Google validé avec tolérance horloge étendue (%ss)',
                        before_iat + 120,
                    )
                except ValueError:
                    payload = None
            if payload is None:
                payload = _verifier_via_tokeninfo_google(token, client_ids)
                if payload:
                    logger.info('Jeton Google validé via tokeninfo (horloge locale décalée)')
        if payload is None:
            raise _message_erreur_verification(verify_error, token_hint, client_ids) from verify_error
    except Exception as exc:
        logger.exception('Erreur réseau ou librairie lors de la vérification Google')
        raise ErreurConnexionGoogle(
            _('Impossible de contacter Google pour vérifier le jeton. Réessayez dans quelques secondes.'),
            code='google_verification_unavailable',
        ) from exc

    return _valider_claims_google(payload, client_ids)


def _generer_username(base: str) -> str:
    """Username unique à partir de l'e-mail ou du nom Google."""
    slug = re.sub(r'[^a-zA-Z0-9_]', '', base.lower())[:30] or 'user'
    candidate = slug
    suffix = 0
    while User.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f'{slug}{suffix}'
        if suffix > 9999:
            candidate = f'{slug}_{secrets.token_hex(3)}'
            break
    return candidate


@transaction.atomic
def connecter_ou_inscrire_via_google(payload: dict) -> tuple[User, bool]:
    """
    Retourne (utilisateur, est_nouveau_compte).
    - Existant via google_sub → connexion
    - Existant via e-mail → liaison du profil Google
    - Sinon → création compte admin + profil Google
    """
    google_sub = payload['sub']
    email = (payload.get('email') or '').strip().lower()
    given_name = (payload.get('given_name') or '').strip()
    family_name = (payload.get('family_name') or '').strip()
    avatar_url = (payload.get('picture') or '').strip()

    profil = (
        ProfilConnexionGoogle.objects.select_related('utilisateur')
        .filter(google_sub=google_sub)
        .first()
    )
    if profil:
        user = profil.utilisateur
        if not user.is_active:
            raise ErreurConnexionGoogle(
                _('Ce compte est désactivé. Contactez le support.'),
                code='account_disabled',
            )
        _maj_profil_google(profil, email, avatar_url)
        return user, False

    user = None
    if email:
        user = User.objects.filter(email__iexact=email).first()

    if user:
        if ProfilConnexionGoogle.objects.filter(utilisateur=user).exists():
            raise ErreurConnexionGoogle(
                _('Ce compte est déjà lié à un autre profil Google.'),
                code='google_already_linked',
            )
        if not user.is_active:
            raise ErreurConnexionGoogle(
                _('Ce compte est désactivé. Contactez le support.'),
                code='account_disabled',
            )
        ProfilConnexionGoogle.objects.create(
            utilisateur=user,
            google_sub=google_sub,
            email_google=email,
            avatar_url=avatar_url,
        )
        return user, False

    username_base = email.split('@')[0] if email else f'google_{google_sub[:8]}'
    user = User.objects.create_user(
        username=_generer_username(username_base),
        email=email,
        first_name=given_name,
        last_name=family_name,
        role='admin',
        is_active=False,
        email_verifie=False,
    )
    user.set_unusable_password()
    user.save(update_fields=['password'])

    ProfilConnexionGoogle.objects.create(
        utilisateur=user,
        google_sub=google_sub,
        email_google=email,
        avatar_url=avatar_url,
    )
    return user, True


def _maj_profil_google(profil: ProfilConnexionGoogle, email: str, avatar_url: str):
    changed = []
    if email and profil.email_google != email:
        profil.email_google = email
        changed.append('email_google')
    if avatar_url and profil.avatar_url != avatar_url:
        profil.avatar_url = avatar_url
        changed.append('avatar_url')
    if changed:
        profil.save(update_fields=[*changed, 'updated_at'])
