"""Actions métier du parcours onboarding (profil, entreprise, finalisation)."""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils.translation import gettext as _

from abonnements.services.licence import build_etat_licence, demarrer_essai_gratuit, get_abonnement_courant
from abonnements.services.limites import build_resume_limites
from inscription.services.bootstrap_saas import assurer_contexte_initial_utilisateur
from inscription.services.email_messaging import envoyer_email_activation_espace
from inscription.services.entreprise_saas import (
    CHAMPS_CONFIG_REQUIS,
    entreprise_est_configuree,
    evaluer_et_marquer_configuration,
    _valeur_valide,
)
from inscription.services.onboarding_status import build_onboarding_status
from inscription.services.profil_saas import champs_profil_manquants, profil_est_complet

logger = logging.getLogger(__name__)


class ErreurOnboarding(Exception):
    def __init__(self, detail, *, title: str | None = None, code: str = 'onboarding_invalide'):
        self.detail = detail
        self.title = title or _('Informations incomplètes')
        self.code = code
        super().__init__(detail)


def _champs_entreprise_manquants(entreprise) -> list[str]:
    manquants = []
    for champ in CHAMPS_CONFIG_REQUIS:
        if not _valeur_valide(getattr(entreprise, champ, None)):
            manquants.append(champ)
    return manquants


@transaction.atomic
def mettre_a_jour_profil_onboarding(user, data: dict) -> dict:
    """PATCH profil — prénom / nom obligatoires."""
    champs_autorises = {'first_name', 'last_name', 'email'}
    updates = {k: v for k, v in data.items() if k in champs_autorises and v is not None}
    if not updates:
        raise ErreurOnboarding(
            _('Aucune donnée de profil fournie.'),
            title=_('Données manquantes'),
        )

    for field in ('first_name', 'last_name'):
        if field in updates:
            updates[field] = str(updates[field]).strip()

    if 'first_name' in updates and not updates['first_name']:
        raise ErreurOnboarding(_('Le prénom est obligatoire.'))
    if 'last_name' in updates and not updates['last_name']:
        raise ErreurOnboarding(_('Le nom est obligatoire.'))

    for attr, value in updates.items():
        setattr(user, attr, value)
    user.save(update_fields=list(updates.keys()))

    if not profil_est_complet(user):
        manquants = champs_profil_manquants(user)
        raise ErreurOnboarding(
            _('Veuillez renseigner votre prénom et votre nom.'),
            code='profil_incomplet',
        )

    assurer_contexte_initial_utilisateur(user)
    return build_onboarding_status(user)


@transaction.atomic
def mettre_a_jour_entreprise_onboarding(user, data: dict, request=None) -> dict:
    """PATCH entreprise — met à jour l'entreprise provisoire existante."""
    if not profil_est_complet(user):
        raise ErreurOnboarding(
            _('Complétez d\'abord votre profil.'),
            title=_('Étape précédente requise'),
            code='profil_requis',
        )

    assurer_contexte_initial_utilisateur(user)
    ent = user.get_entreprise(request)
    if not ent:
        raise ErreurOnboarding(
            _('Aucune entreprise associée. Réessayez dans quelques instants.'),
            title=_('Entreprise introuvable'),
            code='entreprise_introuvable',
        )

    champs_entreprise = {
        'nom', 'secteur', 'pays', 'ville', 'adresse', 'telephone', 'email',
        'responsable', 'nif', 'slogan',
    }
    updates = {k: v for k, v in data.items() if k in champs_entreprise and v is not None}
    if not updates:
        raise ErreurOnboarding(_('Aucune donnée entreprise fournie.'))

    for attr, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(ent, attr, value)
    ent.save(update_fields=list(updates.keys()))
    evaluer_et_marquer_configuration(ent)

    if not entreprise_est_configuree(ent):
        manquants = _champs_entreprise_manquants(ent)
        labels = {
            'nom': _('le nom de l\'entreprise'),
            'email': _('l\'e-mail professionnel'),
            'telephone': _('le téléphone'),
            'adresse': _('l\'adresse'),
            'pays': _('le pays'),
            'responsable': _('le nom du responsable'),
            'secteur': _('le secteur d\'activité'),
        }
        premier = labels.get(manquants[0], manquants[0]) if manquants else _('les informations')
        raise ErreurOnboarding(
            _('Veuillez renseigner %(champ)s.') % {'champ': premier},
            code='entreprise_incomplete',
        )

    return build_onboarding_status(user, request)


@transaction.atomic
def finaliser_onboarding(user, request=None) -> dict:
    """
    POST complete — marque onboarding terminé, assure l'essai, envoie l'e-mail d'activation.
    """
    if not profil_est_complet(user):
        raise ErreurOnboarding(_('Veuillez compléter votre profil.'), code='profil_incomplet')
    assurer_contexte_initial_utilisateur(user)
    ent = user.get_entreprise(request)
    if not entreprise_est_configuree(ent):
        raise ErreurOnboarding(
            _('Veuillez compléter les informations de votre entreprise.'),
            code='entreprise_incomplete',
        )

    abo = get_abonnement_courant(ent.id) if ent else None
    if not abo:
        demarrer_essai_gratuit(ent, user=user)

    user.onboarding_complete = True
    user.save(update_fields=['onboarding_complete'])

    email_envoye = False
    if not user.email_activation_envoye:
        etat = build_etat_licence(ent.id)
        limites = build_resume_limites(ent.id, request)
        email_envoye = envoyer_email_activation_espace(
            user,
            entreprise=ent,
            etat_licence=etat,
            limites_plan=limites,
        )

    status = build_onboarding_status(user, request)
    status['email_activation_sent'] = bool(user.email_activation_envoye)
    status['email_envoye'] = email_envoye
    status['message'] = _(
        'Votre espace UHAKIKAAPP est prêt. '
        'Nous venons de vous envoyer un e-mail pour confirmer l\'ouverture de votre espace.'
    )
    return status


@transaction.atomic
def marquer_welcome_vu(user, request=None) -> dict:
    user.welcome_seen = True
    user.save(update_fields=['welcome_seen'])
    return build_onboarding_status(user, request)


def renvoyer_email_activation(user, request=None) -> dict:
    if not getattr(user, 'onboarding_complete', False):
        raise ErreurOnboarding(
            _('Terminez d\'abord la configuration de votre espace.'),
            title=_('Onboarding incomplet'),
        )
    if getattr(user, 'workspace_activated', False):
        raise ErreurOnboarding(
            _('Votre espace est déjà activé.'),
            title=_('Déjà activé'),
            code='deja_active',
        )
    ent = user.get_entreprise(request)
    etat = build_etat_licence(ent.id) if ent else None
    limites = build_resume_limites(ent.id, request) if ent else None
    envoye = envoyer_email_activation_espace(
        user,
        entreprise=ent,
        etat_licence=etat,
        limites_plan=limites,
        forcer=True,
    )
    return {
        'email_envoye': envoye,
        'message': _('Un nouvel e-mail d\'activation a été envoyé.') if envoye else _(
            'L\'e-mail n\'a pas pu être envoyé. Réessayez plus tard.'
        ),
    }
