"""Réponses API standard pour la vérification d'e-mail."""
from django.conf import settings
from django.utils.translation import gettext as _


def build_reponse_attente_verification(
    user,
    *,
    connexion_google: bool = False,
    est_nouveau_compte: bool = True,
    email_envoye: bool = True,
    email_erreur: str | None = None,
) -> dict:
    if email_envoye:
        message = _(
            'Un message de confirmation a été envoyé à %(email)s. '
            'Cliquez sur le bouton contenu dans cet e-mail pour activer votre compte.'
        ) % {'email': user.email or ''}
    else:
        message = _(
            'Votre compte a été créé, mais l\'e-mail de confirmation n\'a pas pu être envoyé. '
            'Utilisez « Renvoyer » ou contactez le support.'
        )
    body = {
        'statut_verification': 'EN_ATTENTE',
        'email_verifie': False,
        'email': user.email or '',
        'utilisateur_id': user.id,
        'est_nouveau_compte': est_nouveau_compte,
        'connexion_google': connexion_google,
        'email_envoye': email_envoye,
        'message': message,
        'delai_renvoi_secondes': int(getattr(settings, 'EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS', 60)),
        'validite_lien_heures': int(getattr(settings, 'EMAIL_VERIFICATION_TOKEN_HOURS', 24)),
    }
    if email_erreur:
        body['email_erreur'] = email_erreur
    return body


def build_reponse_email_verifie(user, tokens_payload: dict) -> dict:
    from inscription.services.onboarding_status import (
        chemin_redirection_pour_etape,
        resoudre_next_step,
    )

    next_step = resoudre_next_step(user)
    onboarding_path = chemin_redirection_pour_etape(next_step)
    return {
        'success': True,
        'code': 'email_verifie',
        'email_verifie': True,
        'message': _(
            'Adresse e-mail confirmée avec succès. '
            'Poursuivez la configuration de votre profil et de votre entreprise.'
        ),
        'redirection': onboarding_path,
        'next_step': next_step,
        'tokens': {
            'refresh': tokens_payload['refresh'],
            'access': tokens_payload['access'],
        },
        'user': tokens_payload['user'],
        'bootstrap': tokens_payload.get('bootstrap'),
    }
