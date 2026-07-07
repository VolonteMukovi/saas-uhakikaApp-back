"""
État unifié du flow SaaS pour le frontend (dashboard guard, bannières, routes).
"""
from __future__ import annotations

from django.utils.translation import gettext as _

from abonnements.models import AbonnementEntreprise
from abonnements.services.limites import build_resume_limites
from abonnements.services.licence import build_etat_licence
from inscription.services.entreprise_saas import entreprise_est_configuree
from inscription.services.onboarding_status import (
    NEXT_ACTIVATION,
    NEXT_COMPANY,
    NEXT_DASHBOARD,
    NEXT_PROFILE,
    NEXT_REVIEW,
    NEXT_VERIFY_EMAIL,
    NEXT_WELCOME,
    build_onboarding_status,
    chemin_redirection_pour_etape,
    onboarding_metier_autorise,
    resoudre_next_step,
)
from inscription.services.profil_saas import profil_est_complet

# Statuts flow alignés sur FRONTEND_GUIDE_SAAS_FLOW_UHAKIKAAPP.md
STATUT_EMAIL_NON_VERIFIEE = 'en_attente_verification_email'
STATUT_PRE_INSCRIPTION = 'pre_inscription'
STATUT_CREER_ENTREPRISE = 'creer_entreprise_minimale'
STATUT_ONBOARDING_PROFIL = 'onboarding_profil'
STATUT_ONBOARDING_ENTREPRISE = 'onboarding_entreprise'
STATUT_ONBOARDING_REVIEW = 'onboarding_review'
STATUT_ONBOARDING_ACTIVATION = 'onboarding_activation'
STATUT_ONBOARDING_WELCOME = 'onboarding_welcome'
STATUT_DASHBOARD_ACTIF = 'dashboard_actif'
STATUT_DASHBOARD_CONFIG_INCOMPLETE = 'dashboard_configuration_incomplete'
STATUT_DASHBOARD_LICENCE_EXPIREE = 'dashboard_licence_expiree'
STATUT_PENDING_MANUAL = 'pending_manual_activation'
STATUT_PROFIL_INCOMPLET = 'dashboard_profil_incomplet'


def _statut_licence_frontend(etat_licence: dict | None) -> str | None:
    if not etat_licence:
        return None
    statut = etat_licence.get('statut')
    if statut == 'sans_abonnement':
        return 'sans_abonnement'
    if statut == AbonnementEntreprise.STATUT_EN_ATTENTE:
        return 'pending_manual_activation'
    if statut == AbonnementEntreprise.STATUT_EXPIRE:
        return 'licence_expiree'
    if statut == AbonnementEntreprise.STATUT_ESSAI:
        return 'essai_actif'
    if statut == AbonnementEntreprise.STATUT_ACTIF:
        return 'actif'
    if statut == AbonnementEntreprise.STATUT_SUSPENDU:
        return 'suspendu'
    return statut


def build_etat_flow_saas(user, request=None) -> dict:
    """Point central pour DashboardAccessGuard / FeatureAccessGuard côté frontend."""
    eid = getattr(request, 'tenant_id', None) if request else None
    if not eid and user and user.is_authenticated:
        eid = user.get_entreprise_id(request)

    ent = user.get_entreprise(request) if (user and user.is_authenticated and eid) else None
    a_entreprise = ent is not None

    etat_licence = build_etat_licence(ent.id) if ent else None
    limites = build_resume_limites(ent.id, request) if ent else None

    config_ok = entreprise_est_configuree(ent) if ent else False
    profil_ok = profil_est_complet(user) if user and user.is_authenticated else False
    email_ok = bool(user and user.is_authenticated and getattr(user, 'email_verifie', False))
    onboarding_ok = bool(user and getattr(user, 'onboarding_complete', False))
    workspace_ok = bool(user and getattr(user, 'workspace_activated', False))
    welcome_ok = bool(user and getattr(user, 'welcome_seen', False))
    next_step = resoudre_next_step(user, request) if user and user.is_authenticated else NEXT_VERIFY_EMAIL

    licence_active = bool(etat_licence and etat_licence.get('est_actif'))
    en_attente_manuelle = (
        etat_licence and etat_licence.get('statut') == AbonnementEntreprise.STATUT_EN_ATTENTE
    )
    licence_expiree = (
        etat_licence
        and etat_licence.get('statut') == AbonnementEntreprise.STATUT_EXPIRE
    )
    sans_abonnement = bool(
        etat_licence and etat_licence.get('statut') == 'sans_abonnement'
    )

    if not user or not user.is_authenticated:
        statut_flow = STATUT_PRE_INSCRIPTION
    elif not email_ok:
        statut_flow = STATUT_EMAIL_NON_VERIFIEE
    elif next_step == NEXT_PROFILE:
        statut_flow = STATUT_ONBOARDING_PROFIL
    elif next_step == NEXT_COMPANY:
        statut_flow = STATUT_ONBOARDING_ENTREPRISE
    elif next_step == NEXT_REVIEW:
        statut_flow = STATUT_ONBOARDING_REVIEW
    elif next_step == NEXT_ACTIVATION:
        statut_flow = STATUT_ONBOARDING_ACTIVATION
    elif next_step == NEXT_WELCOME:
        statut_flow = STATUT_ONBOARDING_WELCOME
    elif not a_entreprise:
        statut_flow = STATUT_CREER_ENTREPRISE
    elif next_step == NEXT_DASHBOARD and en_attente_manuelle:
        statut_flow = STATUT_PENDING_MANUAL
    elif next_step == NEXT_DASHBOARD and (licence_expiree or not licence_active):
        statut_flow = STATUT_DASHBOARD_LICENCE_EXPIREE
    elif next_step == NEXT_DASHBOARD:
        statut_flow = STATUT_DASHBOARD_ACTIF
    elif not config_ok:
        statut_flow = STATUT_DASHBOARD_CONFIG_INCOMPLETE
    elif not profil_ok:
        statut_flow = STATUT_PROFIL_INCOMPLET
    else:
        statut_flow = STATUT_ONBOARDING_PROFIL

    # Dashboard uniquement après onboarding complet + activation + écran bienvenue
    acces_dashboard = bool(
        user and user.is_authenticated and email_ok and onboarding_ok
        and workspace_ok and welcome_ok
    )

    operations_metier = (
        onboarding_metier_autorise(user, request)
        and licence_active
        and not en_attente_manuelle
    )

    messages = []
    actions = []

    if user and user.is_authenticated and not email_ok:
        messages.append(_(
            'Confirmez votre adresse e-mail pour poursuivre la configuration de votre espace.'
        ))
        actions.append({'code': 'verifier_email', 'url': chemin_redirection_pour_etape(NEXT_VERIFY_EMAIL)})
    elif next_step == NEXT_PROFILE:
        messages.append(_('Complétez votre profil pour continuer la configuration.'))
        actions.append({'code': 'onboarding_profil', 'url': chemin_redirection_pour_etape(NEXT_PROFILE)})
    elif next_step == NEXT_COMPANY:
        messages.append(_('Complétez les informations de votre entreprise.'))
        actions.append({'code': 'onboarding_entreprise', 'url': chemin_redirection_pour_etape(NEXT_COMPANY)})
    elif next_step == NEXT_REVIEW:
        messages.append(_('Vérifiez votre configuration avant de finaliser.'))
        actions.append({'code': 'onboarding_review', 'url': chemin_redirection_pour_etape(NEXT_REVIEW)})
    elif next_step == NEXT_ACTIVATION:
        messages.append(_(
            'Consultez votre boîte e-mail et cliquez sur le lien pour activer votre espace.'
        ))
        actions.append({'code': 'onboarding_activation', 'url': chemin_redirection_pour_etape(NEXT_ACTIVATION)})
    elif next_step == NEXT_WELCOME:
        messages.append(_('Bienvenue sur UHAKIKAAPP ! Finalisez votre accueil.'))
        actions.append({'code': 'onboarding_welcome', 'url': chemin_redirection_pour_etape(NEXT_WELCOME)})
    elif not a_entreprise:
        messages.append(_(
            'Créez votre espace entreprise pour accéder au dashboard.'
        ))
        actions.append({'code': 'creer_entreprise_minimale', 'url': '/onboarding/company-minimal'})
    elif en_attente_manuelle:
        messages.append(_(
            'Votre demande d\'abonnement est en attente de validation. '
            'L\'équipe UHAKIKAAPP activera votre licence après vérification du paiement.'
        ))
        actions.append({'code': 'voir_statut_abonnement', 'url': '/subscription/manual-pending'})
    elif sans_abonnement:
        messages.append(_(
            'Votre essai gratuit est en cours de préparation. Patientez quelques instants.'
        ))
        actions.append({'code': 'preparer_espace', 'url': '/onboarding/bootstrap'})
    elif licence_expiree:
        messages.append(_(
            'Votre licence a expiré. Veuillez renouveler votre abonnement.'
        ))
        actions.append({'code': 'renouveler', 'url': '/subscription/renew'})
    elif not licence_active:
        messages.append(_(
            'Votre licence est inactive. Contactez le support ou renouvelez votre abonnement.'
        ))
        actions.append({'code': 'renouveler', 'url': '/subscription/renew'})
    elif not config_ok:
        messages.append(_(
            'Configuration entreprise incomplète. '
            'Complétez les informations de votre entreprise pour activer toutes les opérations métier.'
        ))
        actions.append({'code': 'completer_entreprise', 'url': '/company/setup'})
    elif not profil_ok:
        messages.append(_(
            'Veuillez compléter votre profil avant d\'effectuer les opérations métier.'
        ))
        actions.append({'code': 'completer_profil', 'url': '/profile/setup'})
    elif statut_flow == STATUT_DASHBOARD_ACTIF:
        messages.append(_(
            'Votre licence est active. Votre entreprise est correctement configurée.'
        ))

    bannieres = []
    if a_entreprise and en_attente_manuelle:
        bannieres.append({
            'code': 'pending_manual_activation',
            'niveau': 'info',
            'titre': _('Activation en attente'),
            'message': messages[-1] if messages else '',
            'action': {'code': 'voir_statut_abonnement', 'url': '/subscription/manual-pending'},
        })
    elif a_entreprise and (licence_expiree or (not licence_active and not en_attente_manuelle and not sans_abonnement)):
        bannieres.append({
            'code': 'licence_expiree',
            'niveau': 'warning',
            'titre': _('Licence expirée'),
            'message': messages[-1] if messages else '',
            'action': {'code': 'renouveler', 'url': '/subscription/renew'},
        })
    if a_entreprise and not config_ok and onboarding_ok:
        bannieres.append({
            'code': 'configuration_incomplete',
            'niveau': 'warning',
            'titre': _('Configuration entreprise incomplète'),
            'message': _(
                'Complétez les informations de votre entreprise pour activer ventes, stock et caisse.'
            ),
            'action': {'code': 'completer_entreprise', 'url': '/company/setup'},
        })
    if user and user.is_authenticated and not profil_ok and onboarding_ok:
        bannieres.append({
            'code': 'profil_incomplet',
            'niveau': 'info',
            'titre': _('Profil incomplet'),
            'message': _('Ajoutez votre prénom et nom pour débloquer certaines actions.'),
            'action': {'code': 'completer_profil', 'url': '/profile/setup'},
        })

    onboarding_status = (
        build_onboarding_status(user, request)
        if user and user.is_authenticated else {}
    )

    if etat_licence and etat_licence.get('est_essai') and licence_active:
        jours = etat_licence.get('jours_restants')
        if jours is not None:
            messages.insert(0, _('Essai gratuit : %(jours)s jours restants.') % {'jours': jours})

    return {
        'authentifie': bool(user and user.is_authenticated),
        'a_entreprise': a_entreprise,
        'entreprise_id': ent.id if ent else None,
        'entreprise_nom': ent.nom if ent else None,
        'configuration_entreprise_complete': config_ok,
        'profil_complet': profil_ok,
        'statut_flow': statut_flow,
        'statut_licence_frontend': _statut_licence_frontend(etat_licence),
        'acces_dashboard': acces_dashboard,
        'operations_metier_autorisees': operations_metier,
        'licence_active': licence_active,
        'activation_manuelle_en_attente': bool(en_attente_manuelle),
        'peut_completer_entreprise': bool(a_entreprise),
        'peut_completer_profil': bool(user and user.is_authenticated),
        'pages_onboarding_autorisees': [
            '/verify-email',
            '/onboarding',
            '/onboarding/profile',
            '/onboarding/company',
            '/onboarding/review',
            '/onboarding/activation',
            '/welcome',
            '/company/setup',
            '/profile/setup',
            '/subscription/manual-pending',
            '/subscription/renew',
            '/onboarding/company-minimal',
        ],
        'onboarding_completed': onboarding_ok,
        'workspace_activated': workspace_ok,
        'welcome_seen': welcome_ok,
        'next_step': next_step,
        'redirection': chemin_redirection_pour_etape(next_step),
        'onboarding': onboarding_status,
        'bannieres': bannieres,
        'etat_licence': etat_licence,
        'limites_plan': limites,
        'messages': messages,
        'actions_recommandees': actions,
        'regles_verification': {
            'authentification': bool(user and user.is_authenticated),
            'email_verifie': email_ok,
            'entreprise': a_entreprise,
            'licence_active': licence_active,
            'configuration_entreprise': config_ok,
            'profil_complet': profil_ok,
            'onboarding_complete': onboarding_ok,
            'workspace_activated': workspace_ok,
            'welcome_seen': welcome_ok,
        },
        'email_verifie': email_ok,
    }
