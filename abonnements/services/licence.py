"""
Services métier : essai gratuit, droits d'accès, demandes d'abonnement.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from abonnements.models import (
    AbonnementEntreprise,
    FormuleAbonnement,
    JournalActivationLicence,
    PaiementAbonnement,
)

DUREE_ESSAI_JOURS = 60  # 2 mois


def _fonctionnalites_essai_complet():
    """Pendant l'essai, toutes les fonctionnalités sont ouvertes."""
    return {
        'articles': True,
        'stock': True,
        'approvisionnement': True,
        'vente_comptant': True,
        'vente_credit': True,
        'clients': True,
        'dettes': True,
        'caisse': True,
        'rapports_simples': True,
        'rapports_avances': True,
        'impression_factures': True,
        'lecteur_code_barres': True,
        'roles_permissions': True,
        'tableaux_bord': True,
        'statistiques': True,
        'exports': True,
        'impression_pos': True,
        'multi_succursales': True,
        'assistance_prioritaire': True,
        'portail_client_autonome': True,
        'chatbot': True,
        'accompagnement_personnalisation': True,
    }


def get_formule_essai() -> FormuleAbonnement:
    formule, _ = FormuleAbonnement.objects.get_or_create(
        code=FormuleAbonnement.CODE_ESSAI,
        defaults={
            'nom': 'Découverte Pro',
            'description': (
                'Testez toute la puissance de UHAKIKAAPP gratuitement pendant 2 mois, '
                'sans restriction fonctionnelle.'
            ),
            'duree_essai_jours': DUREE_ESSAI_JOURS,
            'fonctionnalites': _fonctionnalites_essai_complet(),
            'limites': {'utilisateurs_max': None, 'succursales_max': None},
            'est_visible_catalogue': True,
            'ordre_affichage': 0,
        },
    )
    return formule


def get_abonnement_courant(entreprise_id: int) -> AbonnementEntreprise | None:
    return (
        AbonnementEntreprise.objects.filter(entreprise_id=entreprise_id, est_courant=True)
        .select_related('formule')
        .first()
    )


def _journaliser(entreprise_id, action, abonnement=None, user=None, **details):
    JournalActivationLicence.objects.create(
        entreprise_id=entreprise_id,
        abonnement=abonnement,
        action=action,
        effectue_par=user,
        details=details,
    )


@transaction.atomic
def demarrer_essai_gratuit(entreprise, user=None) -> AbonnementEntreprise:
    """
    Démarre l'essai gratuit de 2 mois à la création d'une entreprise.
    Idempotent : ne recrée pas si un abonnement courant existe déjà.
    """
    existing = get_abonnement_courant(entreprise.id)
    if existing:
        return existing

    formule = get_formule_essai()
    now = timezone.now()
    date_fin = now + timedelta(days=DUREE_ESSAI_JOURS)

    abonnement = AbonnementEntreprise.objects.create(
        entreprise=entreprise,
        formule=formule,
        statut=AbonnementEntreprise.STATUT_ESSAI,
        periode=AbonnementEntreprise.PERIODE_ESSAI,
        date_debut=now,
        date_fin=date_fin,
        est_courant=True,
    )
    _journaliser(
        entreprise.id,
        JournalActivationLicence.ACTION_ESSAI_DEMARRE,
        abonnement=abonnement,
        user=user,
        date_fin=date_fin.isoformat(),
        duree_jours=DUREE_ESSAI_JOURS,
    )
    return abonnement


def synchroniser_statut_expiration(abonnement: AbonnementEntreprise) -> AbonnementEntreprise:
    """Passe en expiré si la date de fin est dépassée."""
    if abonnement.statut not in (
        AbonnementEntreprise.STATUT_ESSAI,
        AbonnementEntreprise.STATUT_ACTIF,
    ):
        return abonnement
    if abonnement.date_fin and abonnement.date_fin < timezone.now():
        abonnement.statut = AbonnementEntreprise.STATUT_EXPIRE
        abonnement.save(update_fields=['statut', 'updated_at'])
        _journaliser(
            abonnement.entreprise_id,
            JournalActivationLicence.ACTION_EXPIRATION,
            abonnement=abonnement,
        )
    return abonnement


def build_etat_licence(entreprise_id: int) -> dict:
    """État licence pour API / middleware."""
    abonnement = get_abonnement_courant(entreprise_id)
    if not abonnement:
        return {
            'a_licence': False,
            'statut': 'aucun',
            'est_actif': False,
            'est_essai': False,
            'formule_code': None,
            'formule_nom': None,
            'date_fin': None,
            'jours_restants': 0,
            'fonctionnalites': {},
            'limites': {},
            'message': _('Aucun abonnement actif. Veuillez souscrire à une formule.'),
        }

    abonnement = synchroniser_statut_expiration(abonnement)
    est_essai = abonnement.statut == AbonnementEntreprise.STATUT_ESSAI
    est_actif = abonnement.est_actif

    fonctionnalites = dict(abonnement.formule.fonctionnalites or {})
    limites = dict(abonnement.formule.limites or {})

    # Pendant l'essai : accès complet
    if est_essai and est_actif:
        fonctionnalites = _fonctionnalites_essai_complet()
        limites = {'utilisateurs_max': None, 'succursales_max': None}

    message = ''
    if not est_actif:
        if abonnement.statut == AbonnementEntreprise.STATUT_EXPIRE:
            message = _('Votre abonnement a expiré. Veuillez renouveler pour continuer.')
        elif abonnement.statut == AbonnementEntreprise.STATUT_EN_ATTENTE:
            message = _('Votre demande d\'abonnement est en attente de validation.')
        elif abonnement.statut == AbonnementEntreprise.STATUT_SUSPENDU:
            message = _('Votre accès a été suspendu. Contactez le support.')

    return {
        'a_licence': True,
        'abonnement_id': abonnement.id,
        'statut': abonnement.statut,
        'est_actif': est_actif,
        'est_essai': est_essai,
        'formule_code': abonnement.formule.code,
        'formule_nom': abonnement.formule.nom,
        'periode': abonnement.periode,
        'date_debut': abonnement.date_debut,
        'date_fin': abonnement.date_fin,
        'jours_restants': abonnement.jours_restants,
        'fonctionnalites': fonctionnalites,
        'limites': limites,
        'activation_manuelle': abonnement.activation_manuelle,
        'message': message,
    }


def entreprise_a_acces_complet(entreprise_id: int) -> bool:
    etat = build_etat_licence(entreprise_id)
    return bool(etat.get('est_actif'))


def fonctionnalite_autorisee(entreprise_id: int, cle: str) -> bool:
    etat = build_etat_licence(entreprise_id)
    if not etat.get('est_actif'):
        return False
    return bool(etat.get('fonctionnalites', {}).get(cle, False))


@transaction.atomic
def demander_abonnement(entreprise, formule_code: str, periode: str, user=None) -> AbonnementEntreprise:
    """
    Enregistre une demande d'abonnement payant (en attente de paiement / validation manuelle).
    """
    try:
        formule = FormuleAbonnement.objects.get(code=formule_code, est_active=True)
    except FormuleAbonnement.DoesNotExist as exc:
        raise ValueError(_('Formule d\'abonnement introuvable.')) from exc

    if formule.code in (FormuleAbonnement.CODE_ESSAI, 'essai_gratuit'):
        raise ValueError(_('La formule essai ne peut pas être souscrite manuellement.'))

    if periode not in (
        AbonnementEntreprise.PERIODE_MENSUEL,
        AbonnementEntreprise.PERIODE_ANNUEL,
    ):
        raise ValueError(_('Période invalide.'))

    courant = get_abonnement_courant(entreprise.id)
    if courant and courant.statut == AbonnementEntreprise.STATUT_EN_ATTENTE:
        raise ValueError(_('Une demande est déjà en attente de validation.'))

    montant = (
        formule.prix_mensuel if periode == AbonnementEntreprise.PERIODE_MENSUEL else formule.prix_annuel
    )

    # Marquer l'ancien comme non courant si on remplace par une demande
    if courant:
        courant.est_courant = False
        courant.save(update_fields=['est_courant', 'updated_at'])

    abonnement = AbonnementEntreprise.objects.create(
        entreprise=entreprise,
        formule=formule,
        statut=AbonnementEntreprise.STATUT_EN_ATTENTE,
        periode=periode,
        est_courant=True,
    )
    PaiementAbonnement.objects.create(
        abonnement=abonnement,
        montant=Decimal(montant),
        devise=formule.devise,
        statut=PaiementAbonnement.STATUT_EN_ATTENTE,
        fournisseur=PaiementAbonnement.FOURNISSEUR_MANUEL,
    )
    _journaliser(
        entreprise.id,
        JournalActivationLicence.ACTION_DEMANDE_ABONNEMENT,
        abonnement=abonnement,
        user=user,
        formule=formule.code,
        periode=periode,
        montant=str(montant),
    )
    return abonnement


@transaction.atomic
def activer_abonnement_manuellement(
    abonnement: AbonnementEntreprise,
    admin_user,
    notes: str = '',
) -> AbonnementEntreprise:
    """Activation par superadmin après vérification du paiement manuel."""
    if abonnement.statut != AbonnementEntreprise.STATUT_EN_ATTENTE:
        raise ValueError(_('Seul un abonnement en attente peut être activé manuellement.'))

    now = timezone.now()
    if abonnement.periode == AbonnementEntreprise.PERIODE_ANNUEL:
        date_fin = now + timedelta(days=365)
    elif abonnement.periode == AbonnementEntreprise.PERIODE_MENSUEL:
        date_fin = now + timedelta(days=30)
    else:
        date_fin = now + timedelta(days=30)

    abonnement.statut = AbonnementEntreprise.STATUT_ACTIF
    abonnement.date_debut = now
    abonnement.date_fin = date_fin
    abonnement.activation_manuelle = True
    abonnement.active_par = admin_user
    abonnement.notes = notes or abonnement.notes
    abonnement.est_courant = True
    abonnement.save()

    paiement = abonnement.paiements.filter(statut=PaiementAbonnement.STATUT_EN_ATTENTE).first()
    if paiement:
        paiement.statut = PaiementAbonnement.STATUT_CONFIRME
        paiement.confirme_at = now
        paiement.confirme_par = admin_user
        paiement.save(update_fields=['statut', 'confirme_at', 'confirme_par', 'updated_at'])

    _journaliser(
        abonnement.entreprise_id,
        JournalActivationLicence.ACTION_ACTIVATION_MANUELLE,
        abonnement=abonnement,
        user=admin_user,
        date_fin=date_fin.isoformat(),
        notes=notes,
    )
    return abonnement


def get_abonnement_en_attente(entreprise_id: int) -> AbonnementEntreprise | None:
    return (
        AbonnementEntreprise.objects.filter(
            entreprise_id=entreprise_id,
            est_courant=True,
            statut=AbonnementEntreprise.STATUT_EN_ATTENTE,
        )
        .select_related('formule', 'entreprise')
        .first()
    )


@transaction.atomic
def activer_abonnement_pour_entreprise(
    entreprise_id: int,
    admin_user,
    notes: str = '',
) -> AbonnementEntreprise:
    """Active l'abonnement en attente de l'entreprise (superadmin plateforme)."""
    abonnement = get_abonnement_en_attente(entreprise_id)
    if not abonnement:
        abonnement = (
            AbonnementEntreprise.objects.filter(
                entreprise_id=entreprise_id,
                statut=AbonnementEntreprise.STATUT_EN_ATTENTE,
            )
            .order_by('-created_at')
            .first()
        )
    if not abonnement:
        raise ValueError(_('Aucun abonnement en attente pour cette entreprise.'))
    return activer_abonnement_manuellement(abonnement, admin_user, notes=notes)
