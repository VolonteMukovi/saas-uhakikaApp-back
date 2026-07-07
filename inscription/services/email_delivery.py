"""En-têtes et journalisation des e-mails transactionnels."""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from inscription.models import EmailEnvoiLog

logger = logging.getLogger(__name__)

_warned_resend_dev = False


def expediteur_est_sandbox_resend(from_email: str | None = None) -> bool:
    addr = (from_email or resolve_from_email()).lower()
    return '@resend.dev' in addr


def classifier_erreur_smtp(detail: str) -> str:
    d = (detail or '').lower()
    if any(
        phrase in d
        for phrase in (
            'domain is not verified',
            'domain not authenticated',
            'not authenticated',
            'sender is not valid',
            'sender not valid',
            'invalid sender',
        )
    ):
        return 'domaine_non_verifie'
    if any(
        phrase in d
        for phrase in (
            'only send testing emails',
            'you can only send testing emails',
            'you can only send',
            'verify a domain at resend.com/domains',
            'testing emails to your own',
        )
    ):
        return 'destinataire_sandbox_resend'
    if any(
        phrase in d
        for phrase in (
            'sender',
            'from address',
            'not authorized',
            'unauthorized sender',
        )
    ) and 'domain' not in d:
        return 'expediteur_non_autorise'
    return 'erreur_envoi'


def verifier_destinataire_resend(destinataire: str, *, from_email: str | None = None) -> str | None:
    """
    Retourne un code d'erreur si l'envoi sera refusé par Resend (sandbox).
    None = envoi autorisé.
    """
    if not expediteur_est_sandbox_resend(from_email):
        return None
    owner = getattr(settings, 'RESEND_SANDBOX_OWNER_EMAIL', '').strip().lower()
    cible = (destinataire or '').strip().lower()
    if owner and cible and cible != owner:
        return 'destinataire_sandbox_resend'
    if owner and cible and cible == owner:
        return None
    # Sans e-mail propriétaire configuré : avertir mais tenter l'envoi SMTP
    return None


def resolve_from_email() -> str:
    """Expéditeur unique pour confirmation et bienvenue."""
    global _warned_resend_dev
    from_email = (
        getattr(settings, 'EMAIL_TRANSACTIONAL_FROM', '').strip()
        or getattr(settings, 'DEFAULT_FROM_EMAIL', '').strip()
    )
    if '@resend.dev' in from_email.lower() and not _warned_resend_dev:
        _warned_resend_dev = True
        logger.warning(
            'Expéditeur @resend.dev détecté : mode test limité. '
            'Utilisez Brevo (smtp-relay.brevo.com) avec noreply@uhakikaapp.store.'
        )
    return from_email


def build_transactional_headers(*, email_type: str, destinataire: str) -> dict[str, str]:
    """
    En-têtes transactionnels sobres (évite Importance/List-ID qui déclenchent le spam).
    """
    support = getattr(settings, 'SUPPORT_EMAIL', 'support@uhakikaapp.store')
    return {
        'Reply-To': support,
        'Auto-Submitted': 'auto-generated',
        'X-Auto-Response-Suppress': 'All',
        'X-Entity-Ref-ID': f'{email_type}-{uuid.uuid4().hex[:16]}',
    }


def creer_journal_email(
    *,
    utilisateur,
    type_email: str,
    destinataire: str,
    sujet: str,
) -> EmailEnvoiLog:
    return EmailEnvoiLog.objects.create(
        utilisateur=utilisateur,
        type_email=type_email,
        destinataire=destinataire,
        sujet=sujet,
        statut=EmailEnvoiLog.STATUT_PREPARE,
    )


def marquer_email_envoye(journal: EmailEnvoiLog) -> None:
    journal.statut = EmailEnvoiLog.STATUT_ENVOYE
    journal.envoye_le = timezone.now()
    journal.save(update_fields=['statut', 'envoye_le'])


def marquer_email_echec(journal: EmailEnvoiLog, *, code: str | None, details: str = '') -> None:
    journal.statut = EmailEnvoiLog.STATUT_ECHEC
    journal.code_erreur = code or 'erreur_envoi'
    journal.details = (details or '')[:2000]
    journal.save(update_fields=['statut', 'code_erreur', 'details'])


def verification_deja_envoyee_recemment(user, *, minutes: int = 2) -> bool:
    """Évite un double envoi immédiat sur le même événement d'inscription."""
    if not user or not user.pk:
        return False
    seuil = timezone.now() - timedelta(minutes=minutes)
    return EmailEnvoiLog.objects.filter(
        utilisateur=user,
        type_email=EmailEnvoiLog.TYPE_VERIFICATION,
        statut=EmailEnvoiLog.STATUT_ENVOYE,
        envoye_le__gte=seuil,
    ).exists()
