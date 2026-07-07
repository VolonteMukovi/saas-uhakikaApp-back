"""Création entreprise minimale et configuration SaaS."""
from __future__ import annotations

from django.contrib.auth import get_user_model
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
    if complet:
        from users.models import Membership
        for membership in Membership.objects.filter(
            entreprise=entreprise, role='admin', is_active=True,
        ).select_related('user'):
            user = membership.user
            if getattr(user, 'onboarding_complete', False):
                continue
            from inscription.services.welcome_email import envoyer_bienvenue_si_eligible
            envoyer_bienvenue_si_eligible(user)
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
    Crée ou met à jour l'entreprise provisoire du parcours onboarding.
    Ne crée jamais une seconde entreprise si l'utilisateur en a déjà une active.
    """
    from users.models import Membership
    from users.services.membership_context import get_primary_membership
    from inscription.services.entreprise_onboarding import consolider_entreprises_utilisateur

    User = get_user_model()
    User.objects.select_for_update().get(pk=user.pk)
    consolider_entreprises_utilisateur(user)

    membership = get_primary_membership(user)
    entreprise_existante = membership.entreprise if membership else None
    mis_a_jour = False

    if entreprise_existante:
        if entreprise_est_configuree(entreprise_existante) and entreprise_existante.configuration_complete:
            raise ValueError(_('Votre entreprise est déjà configurée. Modifiez-la depuis les paramètres.'))
        entreprise = _mettre_a_jour_entreprise_provisoire(
            entreprise_existante,
            user,
            nom=nom,
            pays=pays,
            ville=ville,
            email_entreprise=email_entreprise,
        )
        mis_a_jour = True
    else:
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
        'configuration_complete': entreprise.configuration_complete,
        'mis_a_jour': mis_a_jour,
        'source_activation': source_activation,
    }

    if _est_plan_essai(formule_code, periode) or source_activation == 'essai_gratuit':
        abo = get_abonnement_courant(entreprise.id) or demarrer_essai_gratuit(entreprise, user=user)
        result['abonnement_id'] = abo.id
        result['statut_licence'] = abo.statut
        result['message'] = (
            _('Entreprise mise à jour.') if mis_a_jour
            else _('Découverte Pro activé pour 2 mois. Accès complet au dashboard.')
        )
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


def _mettre_a_jour_entreprise_provisoire(
    entreprise: Entreprise,
    user,
    *,
    nom: str,
    pays: str = '',
    ville: str = '',
    email_entreprise: str = '',
) -> Entreprise:
    entreprise.nom = nom.strip()
    if pays:
        entreprise.pays = pays.strip()
    if ville:
        entreprise.adresse = ville.strip()
    if email_entreprise:
        entreprise.email = email_entreprise.strip()
    elif user.email and not _valeur_valide(entreprise.email):
        entreprise.email = user.email.strip()
    resp = (user.get_full_name() or user.username or '').strip()
    if resp and not _valeur_valide(entreprise.responsable):
        entreprise.responsable = resp
    entreprise.save()
    return entreprise


def entreprise_contient_donnees_metier(entreprise: Entreprise) -> bool:
    """True si l'entreprise a des données opérationnelles."""
    from caisse.models import MouvementCaisse, SessionCaisse, TypeCaisse
    from stock.models import Article, ClientEntreprise, DetteClient, Entree, Sortie
    from users.models import Membership

    eid = entreprise.id
    checks = [
        Article.objects.filter(entreprise_id=eid).exists(),
        Entree.objects.filter(entreprise_id=eid).exists(),
        Sortie.objects.filter(entreprise_id=eid).exists(),
        ClientEntreprise.objects.filter(entreprise_id=eid).exists(),
        DetteClient.objects.filter(entreprise_id=eid).exists(),
        TypeCaisse.objects.filter(entreprise_id=eid).exists(),
        MouvementCaisse.objects.filter(entreprise_id=eid).exists(),
        SessionCaisse.objects.filter(entreprise_id=eid).exists(),
        Membership.objects.filter(entreprise_id=eid).count() > 1,
    ]
    return any(checks)
