"""Création entreprise minimale et configuration SaaS."""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext as _

from abonnements.models import AbonnementEntreprise, FormuleAbonnement, PaiementAbonnement
from abonnements.services.licence import demarrer_essai_gratuit, get_abonnement_courant
from abonnements.services.paiement import ErreurPaiement, initier_paiement_en_ligne
from stock.models import Entreprise

PLACEHOLDER = 'À compléter'

CHAMPS_CONFIG_REQUIS = (
    'nom', 'email', 'telephone', 'adresse', 'pays', 'responsable', 'secteur',
)


def _valeur_valide(val: str | None) -> bool:
    v = (val or '').strip()
    return bool(v) and v not in (PLACEHOLDER, '-', 'N/A')


def entreprise_est_configuree(entreprise: Entreprise | None) -> bool:
    if not entreprise:
        return False
    if getattr(entreprise, 'configuration_complete', False):
        return True
    return all(_valeur_valide(getattr(entreprise, champ, None)) for champ in CHAMPS_CONFIG_REQUIS)


def evaluer_et_marquer_configuration(entreprise: Entreprise) -> bool:
    complet = all(_valeur_valide(getattr(entreprise, champ, None)) for champ in CHAMPS_CONFIG_REQUIS)
    if entreprise.configuration_complete != complet:
        entreprise.configuration_complete = complet
        entreprise.save(update_fields=['configuration_complete'])
    return complet


def _est_plan_essai(formule_code: str, periode: str) -> bool:
    return (
        formule_code in (FormuleAbonnement.CODE_ESSAI, 'essai', 'essai_gratuit')
        or periode == AbonnementEntreprise.PERIODE_ESSAI
    )


@transaction.atomic
def creer_entreprise_minimale(
    user,
    *,
    nom: str,
    pays: str = '',
    ville: str = '',
    email_entreprise: str = '',
    formule_code: str = FormuleAbonnement.CODE_ESSAI,
    periode: str = AbonnementEntreprise.PERIODE_ESSAI,
    source_activation: str = 'essai_gratuit',
    fournisseur_paiement: str | None = None,
) -> dict:
    """
    Crée entreprise minimale + membership admin + licence selon le plan choisi.
    Redirection dashboard possible immédiatement après.
    """
    from users.models import Membership

    if Membership.objects.filter(user=user, is_active=True).exists():
        raise ValueError(_('Vous avez déjà une entreprise active.'))

    email = email_entreprise or user.email or f'{user.username}@uhakikaapp.local'
    adresse = ville or pays or PLACEHOLDER

    entreprise = Entreprise.objects.create(
        nom=nom.strip(),
        pays=(pays or PLACEHOLDER).strip(),
        adresse=adresse.strip() if adresse else PLACEHOLDER,
        email=email.strip(),
        telephone=PLACEHOLDER,
        secteur=PLACEHOLDER,
        nif=PLACEHOLDER,
        responsable=(user.get_full_name() or user.username or PLACEHOLDER).strip(),
        configuration_complete=False,
    )
    Membership.objects.create(user=user, entreprise=entreprise, role='admin', is_active=True)

    result = {
        'entreprise_id': entreprise.id,
        'entreprise_nom': entreprise.nom,
        'configuration_complete': False,
        'source_activation': source_activation,
    }

    if _est_plan_essai(formule_code, periode) or source_activation == 'essai_gratuit':
        abo = get_abonnement_courant(entreprise.id) or demarrer_essai_gratuit(entreprise, user=user)
        result['abonnement_id'] = abo.id
        result['statut_licence'] = abo.statut
        result['message'] = _('Découverte Pro activé pour 2 mois. Accès complet au dashboard.')
        return result

    # Plan payant : remplacer l'essai auto (signal) par demande / paiement
    if source_activation == 'paiement_en_ligne' and fournisseur_paiement:
        code_formule = formule_code if formule_code != 'essai_gratuit' else FormuleAbonnement.CODE_ESSENTIEL
        try:
            session = initier_paiement_en_ligne(
                entreprise,
                code_formule,
                periode,
                fournisseur_paiement,
                user=user,
            )
        except ErreurPaiement as exc:
            raise ValueError(str(exc)) from exc
        result.update(session)
        result['statut_licence'] = AbonnementEntreprise.STATUT_EN_ATTENTE
        result['message'] = _('Paiement initié. La licence sera activée après confirmation du gateway.')
        return result

    # Activation manuelle
    from abonnements.services.licence import demander_abonnement
    code_formule = formule_code if formule_code not in ('essai', 'essai_gratuit') else FormuleAbonnement.CODE_ESSENTIEL
    periode_payante = periode if periode in (
        AbonnementEntreprise.PERIODE_MENSUEL,
        AbonnementEntreprise.PERIODE_ANNUEL,
    ) else AbonnementEntreprise.PERIODE_MENSUEL
    abo = demander_abonnement(entreprise, code_formule, periode_payante, user=user)
    result['abonnement_id'] = abo.id
    result['statut_licence'] = AbonnementEntreprise.STATUT_EN_ATTENTE
    result['statut_frontend'] = 'pending_manual_activation'
    result['message'] = _(
        'Votre demande d\'abonnement a été enregistrée. '
        'L\'équipe UHAKIKAAPP va vérifier votre paiement et activer votre licence.'
    )
    return result
