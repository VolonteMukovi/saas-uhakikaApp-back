"""
État session caisse active — payload canonique pour le frontend (source de vérité).
"""
from __future__ import annotations

from typing import Optional

from caisse.models import SessionCaisse
from caisse.services.session_caisse import calculer_totaux_session


def serialize_session_active(session: SessionCaisse) -> dict:
    """
    Session normalisée pour l'UI : champs plats + objets imbriqués.
    Le frontend peut comparer ``type_caisse_id`` / ``devise_id`` sans parser les objets.
    """
    tc = session.type_caisse
    dev = session.devise
    totaux = calculer_totaux_session(session) if session.statut == 'OUVERTE' else None
    solde_actuel = totaux['solde_theorique'] if totaux else session.solde_theorique

    payload = {
        'id': session.pk,
        'numero': session.numero,
        'statut': session.statut,
        'type_caisse_id': session.type_caisse_id,
        'devise_id': session.devise_id,
        'entreprise_id': session.entreprise_id,
        'succursale_id': session.succursale_id,
        'caisse_id': session.type_caisse_id,
        'caisse': (tc.nom or tc.libelle) if tc else '',
        'caisse_libelle': tc.libelle_affiche if tc else '',
        'caisse_code_type': tc.code_type if tc else '',
        'devise': dev.sigle if dev else '',
        'devise_sigle': dev.sigle if dev else '',
        'devise_symbole': dev.symbole if dev else '',
        'date_ouverture': session.ouvert_le.isoformat() if session.ouvert_le else None,
        'ouvert_le': session.ouvert_le.isoformat() if session.ouvert_le else None,
        'cloture_le': session.cloture_le.isoformat() if session.cloture_le else None,
        'solde_ouverture': str(session.solde_ouverture or 0),
        'solde_actuel': str(solde_actuel if solde_actuel is not None else session.solde_ouverture or 0),
        'est_legacy': session.est_legacy,
    }

    if tc:
        payload['type_caisse'] = {
            'id': tc.pk,
            'nom': tc.nom,
            'libelle': tc.libelle,
            'code_type': tc.code_type,
            'est_defaut': tc.est_defaut,
        }
    else:
        payload['type_caisse'] = None

    if dev:
        payload['devise_detail'] = {
            'id': dev.pk,
            'sigle': dev.sigle,
            'symbole': dev.symbole,
            'nom': dev.nom,
            'est_principal': dev.est_principal,
        }
    else:
        payload['devise_detail'] = None

    if totaux:
        payload['totaux_courants'] = {
            'total_entrees': str(totaux['total_entrees']),
            'total_sorties': str(totaux['total_sorties']),
            'solde_theorique': str(totaux['solde_theorique']),
            'nombre_mouvements': totaux['nombre_mouvements'],
        }

    return payload


def build_active_state_response(
    *,
    session: Optional[SessionCaisse] = None,
    sessions: Optional[list] = None,
) -> dict:
    """
    Réponse canonique ``is_open`` + compatibilité ``ouverte``.

    - Une session précise → ``session`` objet
    - Plusieurs sessions ouvertes → ``sessions`` liste + ``session`` = première (principale)
    """
    sessions = sessions or []
    if session is not None:
        sessions = [session] + [s for s in sessions if s.pk != session.pk]

    serialized = [serialize_session_active(s) for s in sessions]
    primary = serialized[0] if serialized else None
    is_open = bool(serialized)

    return {
        'is_open': is_open,
        'ouverte': is_open,
        'session': primary,
        'sessions': serialized,
        'scope': 'caisse_cash_defaut',
    }
