"""Messages d'erreur e-mail pour l'API."""
from django.utils.translation import gettext as _


def message_erreur_envoi_email(code: str | None) -> str:
    if code == 'domaine_non_verifie':
        return _(
            'Le domaine uhakikaapp.store n\'est pas authentifié chez Brevo. '
            'Vérifiez les enregistrements DNS (brevo-code, DKIM, DMARC) sur '
            'https://app.brevo.com puis authentifiez le domaine.'
        )
    if code == 'destinataire_sandbox_resend':
        return _(
            'Expéditeur de test détecté (@resend.dev). '
            'Utilisez Brevo avec DEFAULT_FROM_EMAIL=UhakikaApp <noreply@uhakikaapp.store>.'
        )
    if code == 'expediteur_non_autorise':
        return _(
            'L\'adresse d\'expédition n\'est pas autorisée chez Brevo. '
            'Ajoutez noreply@uhakikaapp.store comme expéditeur dans Brevo '
            '(Expéditeurs et IP) et authentifiez uhakikaapp.store.'
        )
    return _('L\'e-mail de confirmation n\'a pas pu être envoyé. Réessayez ou contactez le support.')
