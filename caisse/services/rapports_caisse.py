"""
Rapports JSON du module caisse — sessions et caisses (tous statuts consultables).
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any, Optional

from django.db.models import Q, Sum
from django.utils import timezone

from caisse.models import EcartCaisse, MouvementCaisse, SessionCaisse, TypeCaisse
from caisse.services.session_caisse import calculer_totaux_session


def _q5(value: Decimal | str | float | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _decimal_str(value) -> str:
    if value is None:
        return '0'
    return str(_q5(value))


def _decimal_num(value) -> float:
    return float(_q5(value))


def format_montant_affiche(montant, devise=None) -> str:
    """Format UI : ``5.00 $``, ``3 566.63 $`` (JSON garde la précision brute)."""
    val = _q5(montant or 0)
    entier, dec = f'{val:.2f}'.split('.')
    entier_fmt = f'{int(entier):,}'.replace(',', ' ')
    texte = f'{entier_fmt}.{dec}'
    symbole = getattr(devise, 'symbole', None) or ''
    if symbole:
        return f'{texte} {symbole}'.strip()
    sigle = getattr(devise, 'sigle', None) or ''
    if sigle:
        return f'{texte} {sigle}'.strip()
    return texte


def parse_rapport_filtres(
    *,
    date_debut=None,
    date_fin=None,
    date_min=None,
    date_max=None,
    devise_id=None,
    type_mouvement=None,
    source=None,
) -> dict:
    return {
        'date_debut': date_debut or date_min,
        'date_fin': date_fin or date_max,
        'devise_id': int(devise_id) if devise_id else None,
        'type_mouvement': type_mouvement if type_mouvement in ('ENTREE', 'SORTIE') else None,
        'source': source or None,
    }


def parse_rapport_filtres_from_request(request) -> dict:
    qp = request.query_params
    return parse_rapport_filtres(
        date_debut=qp.get('date_debut'),
        date_fin=qp.get('date_fin'),
        date_min=qp.get('date_min'),
        date_max=qp.get('date_max'),
        devise_id=qp.get('devise_id'),
        type_mouvement=qp.get('type_mouvement') or qp.get('type'),
        source=qp.get('source') or qp.get('categorie'),
    )


def _serialize_session_header(session: SessionCaisse) -> dict:
    return {
        'id': session.pk,
        'numero': session.numero,
        'statut': session.statut,
        'date_ouverture': session.ouvert_le.isoformat() if session.ouvert_le else None,
        'date_cloture': session.cloture_le.isoformat() if session.cloture_le else None,
        'ouvert_le': session.ouvert_le.isoformat() if session.ouvert_le else None,
        'cloture_le': session.cloture_le.isoformat() if session.cloture_le else None,
        'ouvert_par': session.ouvert_par.username if session.ouvert_par_id else None,
        'cloture_par': session.cloture_par.username if session.cloture_par_id else None,
        'succursale_id': session.succursale_id,
        'entreprise_id': session.entreprise_id,
    }


def _serialize_caisse_header(type_caisse: Optional[TypeCaisse], devise=None) -> dict:
    if not type_caisse:
        return {}
    dev = devise or (type_caisse.devise if type_caisse.devise_id else None)
    return {
        'id': type_caisse.pk,
        'nom': type_caisse.nom or type_caisse.libelle,
        'libelle': type_caisse.libelle_affiche,
        'type': type_caisse.code_type,
        'code_type': type_caisse.code_type,
        'est_defaut': type_caisse.est_defaut,
        'devise': dev.sigle if dev else '',
        'devise_id': dev.pk if dev else None,
        'devise_symbole': dev.symbole if dev else '',
    }


def _serialize_ecart_rapport(session: SessionCaisse) -> Optional[dict]:
    ecart = None
    try:
        ecart = session.ecart
    except EcartCaisse.DoesNotExist:
        ecart = None
    if ecart is None:
        return None

    mvt_ref = ''
    if ecart.mouvement_ajustement_id:
        mvt = ecart.mouvement_ajustement
        mvt_ref = mvt.reference_piece or f'MVT-{mvt.pk}'

    return {
        'id': ecart.pk,
        'type': ecart.type_ecart,
        'type_ecart': ecart.type_ecart,
        'montant': _decimal_num(ecart.montant),
        'montant_brut': _decimal_str(ecart.montant),
        'montant_affiche': format_montant_affiche(ecart.montant, session.devise),
        'statut': ecart.statut,
        'valide_par': ecart.valide_par.username if ecart.valide_par_id else None,
        'valide_par_id': ecart.valide_par_id,
        'date_validation': ecart.valide_le.isoformat() if ecart.valide_le else None,
        'valide_le': ecart.valide_le.isoformat() if ecart.valide_le else None,
        'commentaire': ecart.commentaire or '',
        'mouvement_ajustement': mvt_ref,
        'mouvement_ajustement_id': ecart.mouvement_ajustement_id,
    }


def _build_resume_session(session: SessionCaisse, totaux: dict) -> dict:
    devise = session.devise
    resume = {
        'solde_ouverture': _decimal_num(session.solde_ouverture),
        'solde_ouverture_brut': _decimal_str(session.solde_ouverture),
        'solde_ouverture_affiche': format_montant_affiche(session.solde_ouverture, devise),
        'total_entrees': _decimal_num(totaux['total_entrees']),
        'total_entrees_brut': _decimal_str(totaux['total_entrees']),
        'total_entrees_affiche': format_montant_affiche(totaux['total_entrees'], devise),
        'total_sorties': _decimal_num(totaux['total_sorties']),
        'total_sorties_brut': _decimal_str(totaux['total_sorties']),
        'total_sorties_affiche': format_montant_affiche(totaux['total_sorties'], devise),
        'solde_theorique': _decimal_num(totaux['solde_theorique']),
        'solde_theorique_brut': _decimal_str(totaux['solde_theorique']),
        'solde_theorique_affiche': format_montant_affiche(totaux['solde_theorique'], devise),
        'solde_net': _decimal_num(totaux['solde_theorique']),
        'solde': _decimal_str(totaux['solde_theorique']),
        'nombre_mouvements': totaux['nombre_mouvements'],
    }
    if session.montant_physique is not None:
        resume['montant_physique'] = _decimal_num(session.montant_physique)
        resume['montant_physique_brut'] = _decimal_str(session.montant_physique)
        resume['montant_physique_affiche'] = format_montant_affiche(session.montant_physique, devise)
    if session.ecart_montant is not None:
        resume['ecart'] = _decimal_num(session.ecart_montant)
        resume['ecart_brut'] = _decimal_str(session.ecart_montant)
        resume['ecart_affiche'] = format_montant_affiche(session.ecart_montant, devise)
    return resume


def _mouvements_session_qs(session: SessionCaisse, filtres: Optional[dict] = None):
    filtres = filtres or {}
    qs = session.mouvements.select_related(
        'utilisateur', 'devise', 'type_caisse', 'session_caisse',
    ).order_by('date', 'id')
    if filtres.get('type_mouvement'):
        qs = qs.filter(type=filtres['type_mouvement'])
    if filtres.get('source'):
        qs = qs.filter(categorie=filtres['source'])
    if filtres.get('devise_id'):
        qs = qs.filter(devise_id=filtres['devise_id'])
    return qs


def _serialize_mouvement_ligne(mv: MouvementCaisse, solde_apres: Decimal) -> dict:
    devise = mv.devise
    entree_val = _decimal_num(mv.montant) if mv.type == 'ENTREE' else 0
    sortie_val = _decimal_num(mv.montant) if mv.type == 'SORTIE' else 0
    return {
        'id': mv.pk,
        'date': mv.date.isoformat(),
        'datetime': mv.date.isoformat(),
        'reference': mv.reference_piece or f'MVT-{mv.pk}',
        'type': mv.type,
        'source': mv.categorie,
        'categorie': mv.categorie,
        'description': mv.motif,
        'entree': entree_val,
        'sortie': sortie_val,
        'montant_entree': _decimal_str(mv.montant) if mv.type == 'ENTREE' else '',
        'montant_sortie': _decimal_str(mv.montant) if mv.type == 'SORTIE' else '',
        'entree_affiche': format_montant_affiche(mv.montant, devise) if mv.type == 'ENTREE' else '',
        'sortie_affiche': format_montant_affiche(mv.montant, devise) if mv.type == 'SORTIE' else '',
        'solde_apres': _decimal_num(solde_apres),
        'solde_apres_brut': _decimal_str(solde_apres),
        'solde_apres_affiche': format_montant_affiche(solde_apres, devise),
        'solde_progressif': _decimal_str(solde_apres),
        'utilisateur': mv.utilisateur.username if mv.utilisateur_id else '',
        'utilisateur_id': mv.utilisateur_id,
        'caisse_id': mv.type_caisse_id,
        'caisse': mv.type_caisse.libelle_affiche if mv.type_caisse_id else '',
        'session_id': mv.session_caisse_id,
        'session_numero': mv.session_caisse.numero if mv.session_caisse_id else '',
        'devise': devise.sigle if devise else '',
        'devise_id': mv.devise_id,
    }


def build_mouvements_session(session: SessionCaisse, filtres: Optional[dict] = None) -> list[dict]:
    """Mouvements d'une session uniquement (solde progressif depuis solde d'ouverture)."""
    solde = _q5(session.solde_ouverture or Decimal('0'))
    lignes = []
    for mv in _mouvements_session_qs(session, filtres):
        if mv.type == 'ENTREE':
            solde = _q5(solde + mv.montant)
        else:
            solde = _q5(solde - mv.montant)
        lignes.append(_serialize_mouvement_ligne(mv, solde))
    return lignes


def build_rapport_general_session(session: SessionCaisse) -> dict:
    """Rapport synthétique — consultable quel que soit le statut de la session."""
    totaux = calculer_totaux_session(session)
    payload = {
        'rapport': 'general',
        'scope': 'session',
        'session': _serialize_session_header(session),
        'caisse': _serialize_caisse_header(session.type_caisse, session.devise),
        'resume': _build_resume_session(session, totaux),
        'ecart': _serialize_ecart_rapport(session),
        'genere_le': timezone.now().isoformat(),
    }
    payload.update(_legacy_session_general_fields(session, totaux))
    return payload


def build_rapport_detaille_session(session: SessionCaisse, filtres: Optional[dict] = None) -> dict:
    """Rapport détaillé avec mouvements et solde progressif."""
    filtres = filtres or {}
    totaux = calculer_totaux_session(session)
    mouvements = build_mouvements_session(session, filtres)
    payload = {
        'rapport': 'detaille',
        'scope': 'session',
        'session': _serialize_session_header(session),
        'caisse': _serialize_caisse_header(session.type_caisse, session.devise),
        'resume': _build_resume_session(session, totaux),
        'ecart': _serialize_ecart_rapport(session),
        'mouvements': mouvements,
        'lignes': mouvements,
        'filtres': {k: v for k, v in filtres.items() if v},
        'genere_le': timezone.now().isoformat(),
    }
    payload.update(_legacy_session_detail_fields(session, totaux, mouvements))
    return payload


def _legacy_session_general_fields(session: SessionCaisse, totaux: dict) -> dict:
    """Champs plats historiques (compatibilité API existante)."""
    tc = session.type_caisse
    return {
        'session_id': session.pk,
        'numero': session.numero,
        'caisse': tc.libelle_affiche if tc else '',
        'caisse_id': session.type_caisse_id,
        'caisse_nom': (tc.nom or tc.libelle) if tc else '',
        'caisse_code_type': tc.code_type if tc else '',
        'devise': session.devise.sigle if session.devise_id else '',
        'total_entrees': _decimal_str(totaux['total_entrees']),
        'total_sorties': _decimal_str(totaux['total_sorties']),
        'solde': _decimal_str(totaux['solde_theorique']),
        'nombre_mouvements': totaux['nombre_mouvements'],
        'statut': session.statut,
    }


def _legacy_session_detail_fields(session: SessionCaisse, totaux: dict, mouvements: list) -> dict:
    tc = session.type_caisse
    base = _legacy_session_general_fields(session, totaux)
    base.update({
        'solde_ouverture': _decimal_str(session.solde_ouverture),
        'solde_final': _decimal_str(totaux['solde_theorique']),
        'lignes': mouvements,
    })
    if tc:
        base['caisse_libelle'] = tc.libelle_affiche
    return base


def _mouvements_caisse_qs(type_caisse: TypeCaisse, filtres: Optional[dict] = None):
    filtres = filtres or {}
    qs = MouvementCaisse.objects.filter(type_caisse=type_caisse).select_related(
        'utilisateur', 'devise', 'type_caisse', 'session_caisse',
    ).order_by('date', 'id')
    if filtres.get('date_debut'):
        qs = qs.filter(date__date__gte=filtres['date_debut'])
    if filtres.get('date_fin'):
        qs = qs.filter(date__date__lte=filtres['date_fin'])
    if filtres.get('devise_id'):
        qs = qs.filter(devise_id=filtres['devise_id'])
    if filtres.get('type_mouvement'):
        qs = qs.filter(type=filtres['type_mouvement'])
    if filtres.get('source'):
        qs = qs.filter(categorie=filtres['source'])
    return qs


def build_rapport_general_caisse(type_caisse: TypeCaisse, filtres: Optional[dict] = None) -> dict:
    """Synthèse d'une caisse sur une période (sans session obligatoire)."""
    filtres = filtres or {}
    qs = _mouvements_caisse_qs(type_caisse, filtres)
    agg = qs.aggregate(
        total_entrees=Sum('montant', filter=Q(type='ENTREE')),
        total_sorties=Sum('montant', filter=Q(type='SORTIE')),
    )
    entrees = _q5(agg.get('total_entrees') or Decimal('0'))
    sorties = _q5(agg.get('total_sorties') or Decimal('0'))
    solde_net = _q5(entrees - sorties)
    devise = type_caisse.devise
    resume = {
        'total_entrees': _decimal_num(entrees),
        'total_entrees_brut': _decimal_str(entrees),
        'total_entrees_affiche': format_montant_affiche(entrees, devise),
        'total_sorties': _decimal_num(sorties),
        'total_sorties_brut': _decimal_str(sorties),
        'total_sorties_affiche': format_montant_affiche(sorties, devise),
        'solde_net': _decimal_num(solde_net),
        'solde': _decimal_str(solde_net),
        'solde_affiche': format_montant_affiche(solde_net, devise),
        'nombre_mouvements': qs.count(),
    }
    payload = {
        'rapport': 'general',
        'scope': 'caisse',
        'caisse': _serialize_caisse_header(type_caisse, devise),
        'resume': resume,
        'filtres': {k: v for k, v in filtres.items() if v},
        'genere_le': timezone.now().isoformat(),
    }
    payload.update({
        'caisse_id': type_caisse.pk,
        'caisse_nom': type_caisse.nom or type_caisse.libelle,
        'caisse_libelle': type_caisse.libelle_affiche,
        'caisse_code_type': type_caisse.code_type,
        'devise': devise.sigle if devise else '',
        'total_entrees': _decimal_str(entrees),
        'total_sorties': _decimal_str(sorties),
        'solde': _decimal_str(solde_net),
        'nombre_mouvements': qs.count(),
    })
    return payload


def build_rapport_detaille_caisse(type_caisse: TypeCaisse, filtres: Optional[dict] = None) -> dict:
    """Mouvements d'une caisse sur une période (solde progressif depuis 0)."""
    filtres = filtres or {}
    solde = Decimal('0')
    mouvements = []
    for mv in _mouvements_caisse_qs(type_caisse, filtres):
        if mv.type == 'ENTREE':
            solde = _q5(solde + mv.montant)
        else:
            solde = _q5(solde - mv.montant)
        mouvements.append(_serialize_mouvement_ligne(mv, solde))

    general = build_rapport_general_caisse(type_caisse, filtres)
    general['rapport'] = 'detaille'
    general['scope'] = 'caisse'
    general['mouvements'] = mouvements
    general['lignes'] = mouvements
    general['solde_final'] = _decimal_str(solde)
    general['solde_final_affiche'] = format_montant_affiche(solde, type_caisse.devise)
    return general


def build_mouvements_caisse(type_caisse: TypeCaisse, filtres: Optional[dict] = None) -> dict:
    """Liste paginable des mouvements d'une caisse (période)."""
    filtres = filtres or {}
    mouvements = []
    solde = Decimal('0')
    for mv in _mouvements_caisse_qs(type_caisse, filtres):
        if mv.type == 'ENTREE':
            solde = _q5(solde + mv.montant)
        else:
            solde = _q5(solde - mv.montant)
        mouvements.append(_serialize_mouvement_ligne(mv, solde))
    return {
        'scope': 'caisse',
        'caisse': _serialize_caisse_header(type_caisse, type_caisse.devise),
        'filtres': {k: v for k, v in filtres.items() if v},
        'count': len(mouvements),
        'mouvements': mouvements,
        'genere_le': timezone.now().isoformat(),
    }


def build_mouvements_session_payload(session: SessionCaisse, filtres: Optional[dict] = None) -> dict:
    """Mouvements d'une session (endpoint dédié)."""
    filtres = filtres or {}
    mouvements = build_mouvements_session(session, filtres)
    return {
        'scope': 'session',
        'session': _serialize_session_header(session),
        'caisse': _serialize_caisse_header(session.type_caisse, session.devise),
        'filtres': {k: v for k, v in filtres.items() if v},
        'count': len(mouvements),
        'mouvements': mouvements,
        'genere_le': timezone.now().isoformat(),
    }
