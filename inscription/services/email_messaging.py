"""Envoi des e-mails transactionnels inscription."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from inscription.services.email_verification import (
    build_verification_url,
    creer_jeton_verification,
    peut_renvoyer_verification,
)

logger = logging.getLogger(__name__)


def _envoyer_email(*, sujet: str, destinataire: str, template_txt: str, template_html: str, context: dict) -> bool:
    if not destinataire:
        logger.warning('Envoi e-mail ignoré : destinataire vide (%s)', sujet)
        return False
    try:
        text_body = render_to_string(template_txt, context)
        html_body = render_to_string(template_html, context)
        message = EmailMultiAlternatives(
            subject=sujet,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinataire],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Échec envoi e-mail "%s" à %s', sujet, destinataire)
        return False


def envoyer_email_verification(user, *, forcer: bool = False) -> dict:
    """
    Envoie l'e-mail de confirmation si autorisé.
    Retourne { envoyé, token_clair?, delai_renvoi_secondes, code? }.
    """
    if user.email_verifie:
        return {'envoye': False, 'code': 'deja_verifie', 'delai_renvoi_secondes': 0}

    if not forcer:
        ok, restant, code = peut_renvoyer_verification(user)
        if not ok:
            return {'envoye': False, 'code': code, 'delai_renvoi_secondes': restant}

    token_clair, _ = creer_jeton_verification(user)
    prenom = (user.first_name or user.username or '').strip()
    context = {
        'prenom': prenom or _('Utilisateur'),
        'verification_url': build_verification_url(token_clair),
        'validite_heures': int(getattr(settings, 'EMAIL_VERIFICATION_TOKEN_HOURS', 24)),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@uhakikaapp.store'),
    }
    envoye = _envoyer_email(
        sujet=_('Confirmez votre adresse e-mail — UHAKIKAAPP'),
        destinataire=user.email,
        template_txt='emails/verification_email.txt',
        template_html='emails/verification_email.html',
        context=context,
    )
    return {
        'envoye': envoye,
        'delai_renvoi_secondes': int(getattr(settings, 'EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS', 60)),
    }


def envoyer_email_bienvenue(user, *, entreprise, etat_licence: dict | None, limites_plan: dict | None) -> bool:
    if user.message_bienvenue_envoye:
        return False

    formule = {
        'nom': (etat_licence or {}).get('formule_nom'),
        'code': (etat_licence or {}).get('formule_code'),
        'description': '',
    }
    context = {
        'prenom': (user.first_name or user.username or '').strip() or _('Utilisateur'),
        'nom_complet': user.get_full_name() or user.username,
        'entreprise_nom': getattr(entreprise, 'nom', '') or '',
        'plan_nom': formule.get('nom') or _('Découverte Pro'),
        'plan_code': formule.get('code') or '',
        'plan_description': formule.get('description') or '',
        'periode_libelle': _libelle_periode(etat_licence),
        'date_activation': (etat_licence or {}).get('date_debut'),
        'date_expiration': (etat_licence or {}).get('date_fin'),
        'jours_restants': (etat_licence or {}).get('jours_restants'),
        'utilisateurs_max': (limites_plan or {}).get('utilisateurs_max'),
        'fonctionnalites_cles': _fonctionnalites_plan(formule, limites_plan),
        'dashboard_url': f"{getattr(settings, 'FRONTEND_BASE_URL', '').rstrip('/')}{getattr(settings, 'FRONTEND_DASHBOARD_PATH', '/dashboard')}",
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@uhakikaapp.store'),
    }
    envoye = _envoyer_email(
        sujet=_('Bienvenue sur UHAKIKAAPP — Votre espace est prêt'),
        destinataire=user.email,
        template_txt='emails/welcome_email.txt',
        template_html='emails/welcome_email.html',
        context=context,
    )
    if envoye:
        user.message_bienvenue_envoye = True
        user.save(update_fields=['message_bienvenue_envoye'])
    return envoye


def _libelle_periode(etat_licence: dict | None) -> str:
    if not etat_licence:
        return ''
    if etat_licence.get('est_essai'):
        jours = etat_licence.get('jours_restants')
        if jours is not None:
            return _('Essai gratuit — %(jours)s jours restants') % {'jours': jours}
        return _('Essai gratuit')
    periode = etat_licence.get('periode') or ''
    mapping = {
        'mensuel': _('Mensuel'),
        'annuel': _('Annuel'),
        'essai': _('Essai'),
    }
    return mapping.get(periode, periode)


def _fonctionnalites_plan(formule: dict, limites_plan: dict | None) -> list[str]:
    code = (formule.get('code') or '').lower()
    if code in ('decouverte_pro', 'essai', 'essai_gratuit'):
        return [
            _('Accès complet à toutes les fonctionnalités'),
            _('Utilisateurs illimités pendant l\'essai'),
            _('Stock, ventes, caisse multi-devises, rapports'),
        ]
    if code in ('essentiel', 'starter'):
        max_u = (limites_plan or {}).get('utilisateurs_max') or 2
        return [
            _('Articles, stock, ventes, factures et caisse multi-devises'),
            _('Jusqu\'à %(n)s utilisateurs') % {'n': max_u},
        ]
    if code in ('croissance', 'standard'):
        max_u = (limites_plan or {}).get('utilisateurs_max') or 4
        return [
            _('Gestion commerciale, accompagnement, personnalisations et chatbot'),
            _('Jusqu\'à %(n)s utilisateurs') % {'n': max_u},
        ]
    if code in ('premium_entreprise', 'professionnel', 'entreprise'):
        return [
            _('Utilisateurs illimités'),
            _('Accès à toutes les fonctionnalités disponibles'),
        ]
    return [_('Fonctionnalités selon votre formule active')]
