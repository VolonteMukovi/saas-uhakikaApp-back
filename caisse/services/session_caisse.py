"""
Gestion des sessions de caisse : ouverture, clôture, écarts, rattachement des mouvements.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max, Q, Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from caisse.models import EcartCaisse, MouvementCaisse, SessionCaisse, TypeCaisse
from caisse.services.caisse_defaut import (
    MSG_CAISSE_CASH_FERMEE,
    MSG_CAISSE_DEVISE,
    MSG_CAISSE_INACTIVE,
    MSG_CAISSE_INTRouvable,
    MSG_SESSION_UNIQUEMENT_CASH_DEFAUT,
    caisse_necessite_session,
    get_caisse_defaut_session_scope,
)
from stock.models import Devise


class SessionCaisseError(ValidationError):
    """Erreur métier session de caisse."""


class SessionAlreadyOpenError(SessionCaisseError):
    """Session déjà ouverte — la session existante est attachée pour le frontend."""

    def __init__(self, message, session: SessionCaisse):
        super().__init__(message)
        self.session = session


def _q5(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _session_filter_qs(
    entreprise_id: int,
    succursale_id: Optional[int],
    devise_id: int,
    type_caisse_id: Optional[int] = None,
):
    qs = SessionCaisse.objects.filter(
        entreprise_id=entreprise_id,
        devise_id=devise_id,
    )
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)
    else:
        qs = qs.filter(succursale_id__isnull=True)
    if type_caisse_id is not None:
        qs = qs.filter(type_caisse_id=type_caisse_id)
    return qs


def _resolve_type_caisse_session_id(
    entreprise_id: int,
    succursale_id: Optional[int],
    type_caisse_id: Optional[int],
) -> Optional[int]:
    """Résout l'id caisse pour une recherche de session (cash défaut si absent)."""
    if type_caisse_id is not None:
        tc = TypeCaisse.objects.filter(pk=type_caisse_id, entreprise_id=entreprise_id).first()
        if tc is None:
            return type_caisse_id
        if not caisse_necessite_session(tc):
            return None
        return tc.pk
    caisse_defaut = get_caisse_defaut_session_scope(entreprise_id, succursale_id)
    return caisse_defaut.pk if caisse_defaut else None


def get_session_caisse_ouverte(
    entreprise_id: int,
    succursale_id: Optional[int],
    devise_id: int,
    type_caisse_id: Optional[int] = None,
) -> Optional[SessionCaisse]:
    """
    Retourne la session OUVERTE de la caisse cash par défaut pour le contexte donné.
    Les autres caisses (banque, mobile money) n'ont pas de session : retourne None.
    """
    resolved_id = _resolve_type_caisse_session_id(entreprise_id, succursale_id, type_caisse_id)
    if resolved_id is None:
        return None

    return _session_filter_qs(
        entreprise_id, succursale_id, devise_id, resolved_id,
    ).filter(statut='OUVERTE').first()


def require_session_caisse_ouverte(
    entreprise_id: int,
    succursale_id: Optional[int],
    devise_id: int,
    type_caisse_id: Optional[int] = None,
) -> SessionCaisse:
    """Lève SessionCaisseError si la caisse cash par défaut n'a pas de session ouverte."""
    session = get_session_caisse_ouverte(
        entreprise_id, succursale_id, devise_id, type_caisse_id,
    )
    if session is None:
        raise SessionCaisseError(str(MSG_CAISSE_CASH_FERMEE))
    return session


def get_session_ouverte_for_caisse(
    type_caisse: TypeCaisse,
    succursale_id: Optional[int],
    devise_id: int,
) -> Optional[SessionCaisse]:
    """
    Contrôle central des opérations financières.

    - Caisse cash par défaut : session ouverte obligatoire.
    - Autres caisses : pas de session (retourne None).
    """
    if not type_caisse.is_active:
        raise SessionCaisseError(str(MSG_CAISSE_INACTIVE))

    caisse_devise_id = type_caisse.devise_id
    if not caisse_devise_id:
        return None

    branch = succursale_id
    if branch is not None and type_caisse.succursale_id not in (None, branch):
        raise SessionCaisseError(str(MSG_CAISSE_INTRouvable))

    if type_caisse.succursale_id is not None:
        branch = type_caisse.succursale_id

    if not caisse_necessite_session(type_caisse):
        return None

    return require_session_caisse_ouverte(
        type_caisse.entreprise_id,
        branch,
        caisse_devise_id,
        type_caisse.pk,
    )


def _generer_numero_session(entreprise_id: int) -> str:
    prefix = f'SESS-{entreprise_id:04d}-'
    last = (
        SessionCaisse.objects.filter(numero__startswith=prefix)
        .aggregate(m=Max('numero'))
        .get('m')
    )
    seq = 1
    if last:
        try:
            seq = int(str(last).split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = SessionCaisse.objects.filter(entreprise_id=entreprise_id).count() + 1
    return f'{prefix}{seq:06d}'


def calculer_totaux_session(session: SessionCaisse) -> dict:
    """Calcule entrées, sorties et solde théorique d'une session."""
    agg = session.mouvements.aggregate(
        total_entrees=Sum('montant', filter=Q(type='ENTREE')),
        total_sorties=Sum('montant', filter=Q(type='SORTIE')),
    )
    entrees = _q5(agg.get('total_entrees') or Decimal('0'))
    sorties = _q5(agg.get('total_sorties') or Decimal('0'))
    solde_ouv = _q5(session.solde_ouverture or Decimal('0'))
    solde_theorique = _q5(solde_ouv + entrees - sorties)
    return {
        'total_entrees': entrees,
        'total_sorties': sorties,
        'solde_theorique': solde_theorique,
        'nombre_mouvements': session.mouvements.count(),
    }


def solde_session_courant(session: SessionCaisse) -> Decimal:
    return calculer_totaux_session(session)['solde_theorique']


@transaction.atomic
def ouvrir_session_caisse(
    *,
    entreprise_id: int,
    succursale_id: Optional[int],
    type_caisse_id: int,
    devise_id: int,
    solde_ouverture: Decimal,
    utilisateur,
) -> SessionCaisse:
    type_caisse = TypeCaisse.objects.filter(pk=type_caisse_id, entreprise_id=entreprise_id).first()
    if not type_caisse:
        raise SessionCaisseError(_('Type de caisse introuvable pour cette entreprise.'))
    if not type_caisse.is_active:
        from caisse.services.caisse_defaut import MSG_CAISSE_INACTIVE
        raise SessionCaisseError(str(MSG_CAISSE_INACTIVE))

    if not caisse_necessite_session(type_caisse):
        raise SessionCaisseError(str(MSG_SESSION_UNIQUEMENT_CASH_DEFAUT))

    devise = Devise.objects.filter(pk=devise_id, entreprise_id=entreprise_id).first()
    if not devise:
        raise SessionCaisseError(_('Devise introuvable pour cette entreprise.'))

    existing = get_session_caisse_ouverte(
        entreprise_id, succursale_id, devise_id, type_caisse_id,
    )
    if existing:
        raise SessionAlreadyOpenError(
            _(
                'Une session de caisse est déjà ouverte pour cette caisse, '
                'cette agence et cette devise.'
            ),
            session=existing,
        )

    solde_ouverture = _q5(solde_ouverture)
    if solde_ouverture < 0:
        raise SessionCaisseError(_('Le solde d\'ouverture ne peut pas être négatif.'))

    return SessionCaisse.objects.create(
        numero=_generer_numero_session(entreprise_id),
        type_caisse=type_caisse,
        devise=devise,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        ouvert_par=utilisateur,
        ouvert_le=timezone.now(),
        solde_ouverture=solde_ouverture,
        statut='OUVERTE',
    )


@transaction.atomic
def cloturer_session_caisse(
    *,
    session: SessionCaisse,
    montant_physique: Decimal,
    utilisateur,
    commentaire: str = '',
) -> SessionCaisse:
    if session.statut != 'OUVERTE':
        raise SessionCaisseError(_('Seule une session ouverte peut être clôturée.'))

    if not caisse_necessite_session(session.type_caisse):
        raise SessionCaisseError(str(MSG_SESSION_UNIQUEMENT_CASH_DEFAUT))

    montant_physique = _q5(montant_physique)
    totaux = calculer_totaux_session(session)
    solde_theorique = totaux['solde_theorique']
    ecart = _q5(montant_physique - solde_theorique)

    session.total_entrees = totaux['total_entrees']
    session.total_sorties = totaux['total_sorties']
    session.solde_theorique = solde_theorique
    session.montant_physique = montant_physique
    session.ecart_montant = ecart
    session.cloture_par = utilisateur
    session.cloture_le = timezone.now()
    session.commentaire_cloture = (commentaire or '').strip()

    if ecart == 0:
        session.statut = 'CLOTUREE'
        session.save()
        return session

    type_ecart = 'SURPLUS' if ecart > 0 else 'PERTE'
    session.statut = 'CLOTUREE_EN_ATTENTE_VALIDATION'
    session.save()

    EcartCaisse.objects.create(
        session=session,
        type_ecart=type_ecart,
        montant=_q5(abs(ecart)),
        statut='EN_ATTENTE_VALIDATION',
        declare_par=utilisateur,
        commentaire=session.commentaire_cloture,
    )
    return session


@transaction.atomic
def valider_ecart_caisse(
    *,
    ecart: EcartCaisse,
    administrateur,
    valider: bool = True,
    commentaire: str = '',
) -> EcartCaisse:
    if ecart.statut != 'EN_ATTENTE_VALIDATION':
        raise SessionCaisseError(_('Cet écart n\'est plus en attente de validation.'))

    session = ecart.session
    if session.statut != 'CLOTUREE_EN_ATTENTE_VALIDATION':
        raise SessionCaisseError(_('La session associée n\'est pas en attente de validation.'))

    if not valider:
        ecart.statut = 'REJETE'
        ecart.valide_par = administrateur
        ecart.valide_le = timezone.now()
        ecart.commentaire = (commentaire or ecart.commentaire or '').strip()
        ecart.save()
        session.statut = 'OUVERTE'
        session.cloture_le = None
        session.cloture_par = None
        session.montant_physique = None
        session.ecart_montant = None
        session.solde_theorique = None
        session.save()
        return ecart

    from caisse.services.caisse import creer_mouvement_caisse

    if ecart.type_ecart == 'SURPLUS':
        type_mvt = 'ENTREE'
        categorie = 'AJUSTEMENT_SURPLUS_CAISSE'
    else:
        type_mvt = 'SORTIE'
        categorie = 'AJUSTEMENT_PERTE_CAISSE'

    mvt = creer_mouvement_caisse(
        montant=ecart.montant,
        devise=session.devise,
        type_mouvement=type_mvt,
        entreprise_id=session.entreprise_id,
        succursale_id=session.succursale_id,
        utilisateur=administrateur,
        reference_piece=f'ECART-{ecart.pk}',
        motif=f'Ajustement {ecart.get_type_ecart_display().lower()} session {session.numero}',
        session_caisse=session,
        type_caisse=session.type_caisse,
        categorie=categorie,
        skip_session_check=True,
    )

    ecart.mouvement_ajustement = mvt
    ecart.statut = 'VALIDE'
    ecart.valide_par = administrateur
    ecart.valide_le = timezone.now()
    if commentaire:
        ecart.commentaire = commentaire.strip()
    ecart.save()

    totaux = calculer_totaux_session(session)
    session.total_entrees = totaux['total_entrees']
    session.total_sorties = totaux['total_sorties']
    session.solde_theorique = totaux['solde_theorique']
    session.statut = 'CLOTUREE'
    session.save()
    return ecart


def rapport_caisse_general(session: SessionCaisse) -> dict:
    from caisse.services.rapports_caisse import build_rapport_general_session
    return build_rapport_general_session(session)


def rapport_caisse_detaille(session: SessionCaisse, filtres=None) -> dict:
    from caisse.services.rapports_caisse import build_rapport_detaille_session
    return build_rapport_detaille_session(session, filtres)


def rapport_par_caisse(
    type_caisse: TypeCaisse,
    *,
    date_min=None,
    date_max=None,
    date_debut=None,
    date_fin=None,
    devise_id=None,
    type_mouvement=None,
    source=None,
) -> dict:
    from caisse.services.rapports_caisse import build_rapport_general_caisse, parse_rapport_filtres
    filtres = parse_rapport_filtres(
        date_debut=date_debut,
        date_fin=date_fin,
        date_min=date_min,
        date_max=date_max,
        devise_id=devise_id,
        type_mouvement=type_mouvement,
        source=source,
    )
    return build_rapport_general_caisse(type_caisse, filtres)


def rapport_detaille_par_caisse(
    type_caisse: TypeCaisse,
    *,
    date_min=None,
    date_max=None,
    date_debut=None,
    date_fin=None,
    devise_id=None,
    type_mouvement=None,
    source=None,
) -> dict:
    from caisse.services.rapports_caisse import build_rapport_detaille_caisse, parse_rapport_filtres
    filtres = parse_rapport_filtres(
        date_debut=date_debut,
        date_fin=date_fin,
        date_min=date_min,
        date_max=date_max,
        devise_id=devise_id,
        type_mouvement=type_mouvement,
        source=source,
    )
    return build_rapport_detaille_caisse(type_caisse, filtres)
