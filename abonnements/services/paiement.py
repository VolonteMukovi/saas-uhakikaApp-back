"""
Service paiement en ligne : initiation, webhooks, activation automatique.
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from abonnements.models import (
    AbonnementEntreprise,
    FormuleAbonnement,
    JournalActivationLicence,
    JournalWebhookPaiement,
    PaiementAbonnement,
)
from abonnements.paiements import get_gateway
from abonnements.paiements.gateways.base import NotificationPaiement
from abonnements.services.licence import get_abonnement_courant, _journaliser


class ErreurPaiement(Exception):
    def __init__(self, message, code='erreur_paiement'):
        super().__init__(message)
        self.code = code


FOURNISSEUR_VERS_CODE = {
    PaiementAbonnement.FOURNISSEUR_MAISHAPAY: 'maisha_pay',
    PaiementAbonnement.FOURNISSEUR_FLEXPAY: 'flexpay',
    PaiementAbonnement.FOURNISSEUR_SERDI: 'serdinate_pay',
}


def _code_gateway(fournisseur: str) -> str:
    return FOURNISSEUR_VERS_CODE.get(fournisseur, fournisseur)


def _montant_formule(formule: FormuleAbonnement, periode: str) -> Decimal:
    if periode == AbonnementEntreprise.PERIODE_ANNUEL:
        return Decimal(formule.prix_annuel)
    return Decimal(formule.prix_mensuel)


@transaction.atomic
def _creer_abonnement_et_paiement(
    entreprise,
    formule: FormuleAbonnement,
    periode: str,
    fournisseur: str,
    user=None,
) -> tuple[AbonnementEntreprise, PaiementAbonnement]:
    courant = get_abonnement_courant(entreprise.id)
    if courant and courant.statut == AbonnementEntreprise.STATUT_EN_ATTENTE:
        raise ErreurPaiement(_('Une demande de paiement est déjà en cours.'), code='paiement_en_cours')

    if courant:
        courant.est_courant = False
        courant.save(update_fields=['est_courant', 'updated_at'])

    montant = _montant_formule(formule, periode)
    abonnement = AbonnementEntreprise.objects.create(
        entreprise=entreprise,
        formule=formule,
        statut=AbonnementEntreprise.STATUT_EN_ATTENTE,
        periode=periode,
        est_courant=True,
    )
    paiement = PaiementAbonnement.objects.create(
        abonnement=abonnement,
        montant=montant,
        devise=formule.devise,
        statut=PaiementAbonnement.STATUT_EN_ATTENTE,
        fournisseur=fournisseur,
        reference_interne=str(uuid.uuid4()),
    )
    _journaliser(
        entreprise.id,
        JournalActivationLicence.ACTION_DEMANDE_ABONNEMENT,
        abonnement=abonnement,
        user=user,
        formule=formule.code,
        periode=periode,
        montant=str(montant),
        fournisseur=fournisseur,
        reference_interne=paiement.reference_interne,
    )
    return abonnement, paiement


@transaction.atomic
def initier_paiement_en_ligne(
    entreprise,
    formule_code: str,
    periode: str,
    fournisseur: str,
    user=None,
) -> dict:
    """
    Crée abonnement en attente + session gateway.
    N'active jamais la licence — activation uniquement après webhook confirmé.
    """
    try:
        formule = FormuleAbonnement.objects.get(code=formule_code, est_active=True)
    except FormuleAbonnement.DoesNotExist as exc:
        raise ErreurPaiement(_('Formule introuvable.'), code='formule_introuvable') from exc

    if formule.code == FormuleAbonnement.CODE_ESSAI:
        raise ErreurPaiement(_('La formule essai ne se paie pas en ligne.'), code='formule_interdite')

    if fournisseur not in (
        PaiementAbonnement.FOURNISSEUR_MAISHAPAY,
        PaiementAbonnement.FOURNISSEUR_FLEXPAY,
        PaiementAbonnement.FOURNISSEUR_SERDI,
    ):
        raise ErreurPaiement(_('Fournisseur de paiement invalide.'), code='fournisseur_invalide')

    if periode not in (
        AbonnementEntreprise.PERIODE_MENSUEL,
        AbonnementEntreprise.PERIODE_ANNUEL,
    ):
        raise ErreurPaiement(_('Période invalide.'), code='periode_invalide')

    abonnement, paiement = _creer_abonnement_et_paiement(
        entreprise, formule, periode, fournisseur, user=user,
    )

    gateway = get_gateway(_code_gateway(fournisseur))
    session = gateway.initier_session(paiement)

    paiement.reference_externe = session.get('reference_externe', '')
    paiement.url_paiement = session.get('url_paiement', '')
    paiement.payload_gateway = {'init_session': session}
    paiement.save(update_fields=[
        'reference_externe', 'url_paiement', 'payload_gateway', 'updated_at',
    ])

    return {
        'paiement_id': paiement.id,
        'reference_interne': paiement.reference_interne,
        'abonnement_id': abonnement.id,
        'montant': str(paiement.montant),
        'devise': paiement.devise,
        'fournisseur': fournisseur,
        'statut': paiement.statut,
        **session,
    }


@transaction.atomic
def activer_abonnement_apres_paiement_confirme(
    paiement: PaiementAbonnement,
    notification: NotificationPaiement | None = None,
) -> AbonnementAbonnement:
    """
    Active la licence uniquement si le paiement est confirmé et cohérent.
    Idempotent si déjà confirmé.
    """
    if paiement.statut == PaiementAbonnement.STATUT_CONFIRME:
        return paiement.abonnement

    if paiement.statut != PaiementAbonnement.STATUT_EN_ATTENTE:
        raise ErreurPaiement(_('Ce paiement ne peut plus être confirmé.'), code='paiement_non_confirmable')

    if notification and notification.montant is not None:
        if notification.montant != paiement.montant:
            raise ErreurPaiement(
                _('Montant reçu (%(recu)s) différent du montant attendu (%(attendu)s).')
                % {'recu': notification.montant, 'attendu': paiement.montant},
                code='montant_incoherent',
            )
        if notification.devise and notification.devise.upper() != paiement.devise.upper():
            raise ErreurPaiement(_('Devise incohérente.'), code='devise_incoherente')

    now = timezone.now()
    abonnement = paiement.abonnement
    if abonnement.periode == AbonnementEntreprise.PERIODE_ANNUEL:
        date_fin = now + timedelta(days=365)
    else:
        date_fin = now + timedelta(days=30)

    abonnement.statut = AbonnementEntreprise.STATUT_ACTIF
    abonnement.date_debut = now
    abonnement.date_fin = date_fin
    abonnement.activation_manuelle = False
    abonnement.active_par = None
    abonnement.est_courant = True
    abonnement.save()

    paiement.statut = PaiementAbonnement.STATUT_CONFIRME
    paiement.confirme_at = now
    if notification:
        paiement.reference_externe = notification.reference_externe or paiement.reference_externe
        payload = dict(paiement.payload_gateway or {})
        payload['confirmation'] = notification.brut or {}
        paiement.payload_gateway = payload
    paiement.save(update_fields=[
        'statut', 'confirme_at', 'reference_externe', 'payload_gateway', 'updated_at',
    ])

    _journaliser(
        abonnement.entreprise_id,
        JournalActivationLicence.ACTION_ACTIVATION_PAIEMENT,
        abonnement=abonnement,
        reference_interne=paiement.reference_interne,
        reference_externe=paiement.reference_externe,
        montant=str(paiement.montant),
        fournisseur=paiement.fournisseur,
        date_fin=date_fin.isoformat(),
    )
    return abonnement


@transaction.atomic
def traiter_webhook_paiement(fournisseur: str, payload: dict, ip_source: str | None = None) -> dict:
    """Point d'entrée unique pour tous les webhooks gateways."""
    gateway = get_gateway(fournisseur)
    journal = JournalWebhookPaiement.objects.create(
        fournisseur=fournisseur,
        payload=payload,
        ip_source=ip_source,
    )

    try:
        notification = gateway.parser_notification(payload)
        journal.reference_interne = notification.reference_interne
        journal.save(update_fields=['reference_interne'])

        if not notification.reference_interne:
            journal.statut_traitement = JournalWebhookPaiement.STATUT_ERREUR
            journal.message = 'reference_interne manquante'
            journal.save(update_fields=['statut_traitement', 'message'])
            raise ErreurPaiement(_('Référence interne manquante.'), code='reference_manquante')

        paiement = PaiementAbonnement.objects.select_related('abonnement').filter(
            reference_interne=notification.reference_interne,
        ).first()
        if not paiement:
            journal.statut_traitement = JournalWebhookPaiement.STATUT_ERREUR
            journal.message = 'paiement introuvable'
            journal.save(update_fields=['statut_traitement', 'message'])
            raise ErreurPaiement(_('Paiement introuvable.'), code='paiement_introuvable')

        journal.paiement = paiement
        journal.save(update_fields=['paiement'])

        if notification.statut != 'confirme':
            paiement.statut = PaiementAbonnement.STATUT_ECHEC
            payload_store = dict(paiement.payload_gateway or {})
            payload_store['echec_webhook'] = notification.brut or payload
            paiement.payload_gateway = payload_store
            paiement.save(update_fields=['statut', 'payload_gateway', 'updated_at'])
            journal.statut_traitement = JournalWebhookPaiement.STATUT_TRAITE
            journal.message = 'paiement échoué'
            journal.save(update_fields=['statut_traitement', 'message'])
            return {'statut': 'echec', 'paiement_id': paiement.id}

        if paiement.statut == PaiementAbonnement.STATUT_CONFIRME:
            journal.statut_traitement = JournalWebhookPaiement.STATUT_IGNORE
            journal.message = 'déjà confirmé (idempotent)'
            journal.save(update_fields=['statut_traitement', 'message'])
            return {'statut': 'deja_confirme', 'paiement_id': paiement.id}

        abonnement = activer_abonnement_apres_paiement_confirme(paiement, notification)
        journal.statut_traitement = JournalWebhookPaiement.STATUT_TRAITE
        journal.message = 'licence activée'
        journal.save(update_fields=['statut_traitement', 'message'])
        return {
            'statut': 'confirme',
            'paiement_id': paiement.id,
            'abonnement_id': abonnement.id,
        }

    except ErreurPaiement:
        raise
    except Exception as exc:
        journal.statut_traitement = JournalWebhookPaiement.STATUT_ERREUR
        journal.message = str(exc)[:500]
        journal.save(update_fields=['statut_traitement', 'message'])
        raise


def get_statut_paiement(reference_interne: str, entreprise_id: int | None = None) -> dict | None:
    qs = PaiementAbonnement.objects.select_related('abonnement', 'abonnement__formule').filter(
        reference_interne=reference_interne,
    )
    if entreprise_id:
        qs = qs.filter(abonnement__entreprise_id=entreprise_id)
    paiement = qs.first()
    if not paiement:
        return None
    abo = paiement.abonnement
    return {
        'paiement_id': paiement.id,
        'reference_interne': paiement.reference_interne,
        'reference_externe': paiement.reference_externe,
        'statut': paiement.statut,
        'montant': str(paiement.montant),
        'devise': paiement.devise,
        'fournisseur': paiement.fournisseur,
        'url_paiement': paiement.url_paiement,
        'confirme_at': paiement.confirme_at,
        'abonnement': {
            'id': abo.id,
            'statut': abo.statut,
            'formule_code': abo.formule.code,
            'formule_nom': abo.formule.nom,
            'est_actif': abo.est_actif,
        },
    }
