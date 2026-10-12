"""
Synchronisation des encaissements d'une vente (Sortie) après modification.

Règles (comptabilité de caisse) :

- l'encaissement attendu d'une sortie est le total de ses lignes par devise, uniquement
  pour une vente commerciale au comptant (PAYEE) ; zéro pour une vente à crédit (la dette
  porte le montant) ou une sortie non commerciale ;
- les écritures d'une vente sont l'encaissement d'origine ``VENT-{sortie}-{devise}`` et ses
  ajustements ``AJ-VENT-{sortie}-{devise}-{n}`` ; leur solde net par caisse doit égaler
  l'encaissement attendu ;
- l'encaissement d'origine n'est corrigé sur place que tant que sa session de caisse est
  ouverte (ou pour une caisse sans session : banque, mobile money) ; sinon la différence
  passe par une écriture d'ajustement dans la session ouverte : une session clôturée n'est
  jamais réécrite ;
- changer de caisse transfère l'encaissement : contre-passation dans l'ancienne caisse,
  encaissement dans la nouvelle ;
- toute diminution d'encaissement d'une caisse à session vérifie le solde disponible.
"""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from caisse.models import MouvementCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse
from caisse.services.caisse_defaut import CaisseError, caisse_necessite_session
from caisse.services.currency_conversion import prepare_caisse_movement
from caisse.services.errors import validation_error_message
from caisse.services.session_caisse import (
    SessionCaisseError,
    get_session_ouverte_for_caisse,
    solde_session_courant,
)
from stock.models import Devise, Sortie

MSG_CAISSE_REQUISE_VENTE = 'Type de caisse requis pour encaisser la vente.'


def _quantize(amount) -> Decimal:
    return Decimal(str(amount or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _vent_reference(sortie_id: int, devise_key: str) -> str:
    return f'VENT-{sortie_id}-{devise_key}'


def _ajustement_prefixe(sortie_id: int, devise_key: str) -> str:
    return f'AJ-VENT-{sortie_id}-{devise_key}-'


def encaissement_attendu(sortie: Sortie) -> bool:
    return bool(sortie.est_commerciale) and sortie.statut != 'EN_CREDIT'


def _ecritures_vente(sortie: Sortie) -> list[MouvementCaisse]:
    return list(
        MouvementCaisse.objects.select_for_update()
        .select_related('type_caisse', 'session_caisse', 'devise', 'devise_origine')
        .filter(sortie=sortie)
        .filter(
            Q(reference_piece__startswith=f'VENT-{sortie.pk}-')
            | Q(reference_piece__startswith=f'AJ-VENT-{sortie.pk}-')
        )
        .order_by('id')
    )


def _cle_devise(sortie: Sortie, mv: MouvementCaisse) -> str | None:
    match = re.match(rf'^(?:AJ-)?VENT-{sortie.pk}-(.+?)(?:-\d+)?$', mv.reference_piece or '')
    return match.group(1) if match else None


def _erreur_caisse(exc) -> serializers.ValidationError:
    return serializers.ValidationError({'type_caisse_id': validation_error_message(exc)})


def _session_et_solde(type_caisse: TypeCaisse, succursale_id):
    """Session ouverte de la caisse (None pour une caisse sans session) et solde courant."""
    try:
        session = get_session_ouverte_for_caisse(type_caisse, succursale_id, type_caisse.devise_id)
    except (SessionCaisseError, CaisseError) as exc:
        raise _erreur_caisse(exc) from exc
    if session is None or not caisse_necessite_session(type_caisse):
        return session, None
    return session, solde_session_courant(session)


def _verifier_solde(type_caisse: TypeCaisse, succursale_id, montant_sortant: Decimal) -> None:
    _session, solde = _session_et_solde(type_caisse, succursale_id)
    if solde is not None and montant_sortant > solde:
        raise serializers.ValidationError({
            'montant': (
                f"Solde insuffisant dans la caisse « {type_caisse.libelle_affiche} » pour rembourser "
                f"{montant_sortant} {type_caisse.devise.sigle if type_caisse.devise else ''} "
                f"(solde de la session ouverte : {solde})."
            ),
        })


def _montant_en_devise_caisse(
    montant_operation: Decimal,
    devise_operation: Devise,
    type_caisse: TypeCaisse,
    *,
    entreprise_id: int,
    reference: MouvementCaisse | None,
) -> tuple[Decimal, Decimal | None]:
    """Montant dans la devise de la caisse ; garde le taux de l'encaissement d'origine si possible."""
    if montant_operation <= 0:
        return Decimal('0'), None
    if not type_caisse.devise_id or type_caisse.devise_id == devise_operation.pk:
        return _quantize(montant_operation), None
    if (
        reference is not None
        and reference.taux_conversion
        and reference.devise_origine_id == devise_operation.pk
        and reference.type_caisse_id == type_caisse.pk
    ):
        taux = Decimal(str(reference.taux_conversion))
        return _quantize(montant_operation * taux), taux
    try:
        conversion = prepare_caisse_movement(
            montant_operation=montant_operation,
            devise_operation=devise_operation,
            type_caisse=type_caisse,
            entreprise_id=entreprise_id,
        )
    except CaisseError as exc:
        raise _erreur_caisse(exc) from exc
    return _quantize(conversion.montant_caisse), conversion.taux_conversion


def _modifiable_sur_place(mv: MouvementCaisse) -> bool:
    session = mv.session_caisse
    return session is None or session.statut == 'OUVERTE'


def _net(ecritures: list[MouvementCaisse]) -> Decimal:
    return sum(
        (_quantize(e.montant) if e.type == 'ENTREE' else -_quantize(e.montant) for e in ecritures),
        Decimal('0'),
    )


def _corriger_sur_place(mv: MouvementCaisse, cible: Decimal, montant_operation: Decimal, devise_operation, taux) -> None:
    from stock.services.currency import build_conversion_snapshot

    mv.montant = cible
    if taux is not None and devise_operation is not None:
        mv.montant_origine = _quantize(montant_operation)
        mv.devise_origine = devise_operation
        mv.taux_conversion = taux
    elif cible == 0 and mv.montant_origine is not None:
        mv.montant_origine = Decimal('0')
    snapshot = build_conversion_snapshot(
        entreprise_id=mv.entreprise_id,
        amount=cible,
        devise_source=mv.devise,
    )
    mv.devise_reference = snapshot['devise_reference']
    mv.taux_change = snapshot['taux_change']
    mv.montant_reference = snapshot['montant_reference']
    mv.save()


def _prochain_numero_ajustement(ecritures: list[MouvementCaisse], prefixe: str) -> int:
    numeros = [
        int(e.reference_piece[len(prefixe):])
        for e in ecritures
        if e.reference_piece.startswith(prefixe) and e.reference_piece[len(prefixe):].isdigit()
    ]
    return max(numeros, default=0) + 1


@transaction.atomic
def sync_sortie_cash_movements(
    sortie: Sortie,
    totaux_par_devise: dict,
    *,
    utilisateur=None,
    type_caisse_id: int | None = None,
    old_statut: str | None = None,
    new_statut: str | None = None,
    motif_ajustement: str = '',
) -> list[dict]:
    """
    Aligne les écritures de caisse d'une vente sur son encaissement attendu.
    Retourne la liste des écritures créées ou corrigées (pour le journal de modification).
    """
    sortie = Sortie.objects.select_for_update().get(pk=sortie.pk)
    attendu = encaissement_attendu(sortie)
    ecritures = _ecritures_vente(sortie)

    caisse_demandee = None
    if type_caisse_id:
        caisse_demandee = TypeCaisse.objects.filter(
            pk=type_caisse_id, entreprise_id=sortie.entreprise_id,
        ).select_related('devise').first()
        if caisse_demandee is None:
            raise serializers.ValidationError({'type_caisse_id': 'Caisse introuvable pour cette entreprise.'})

    cles = set(totaux_par_devise) | {k for k in (_cle_devise(sortie, e) for e in ecritures) if k}
    impacts: list[dict] = []
    libelle = motif_ajustement or f'Modification vente #{sortie.pk}'

    for cle in sorted(cles):
        donnees = totaux_par_devise.get(cle) or {}
        total_operation = _quantize(donnees.get('total')) if attendu else Decimal('0')
        devise_operation = donnees.get('devise_obj')
        ecritures_cle = [e for e in ecritures if _cle_devise(sortie, e) == cle]
        origine = next((e for e in ecritures_cle if e.reference_piece == _vent_reference(sortie.pk, cle)), None)

        caisse_cible = caisse_demandee or (origine.type_caisse if origine else None)
        if (
            caisse_cible is None
            and origine is not None
            and ecritures_cle == [origine]
            and _modifiable_sur_place(origine)
        ):
            # Encaissement historique sans caisse : correction sur place, comme auparavant.
            avant = _quantize(origine.montant)
            if avant != total_operation:
                _corriger_sur_place(origine, total_operation, total_operation, devise_operation, None)
                impacts.append(_impact(origine, 'CORRECTION', avant=avant))
            continue
        if total_operation > 0 and caisse_cible is None:
            raise serializers.ValidationError({'type_caisse_id': MSG_CAISSE_REQUISE_VENTE})
        if total_operation > 0 and not caisse_cible.is_active:
            raise serializers.ValidationError({'type_caisse_id': 'Cette opération financière exige une caisse active.'})

        # Première encaisse de cette devise : écriture d'origine standard.
        if origine is None and not ecritures_cle:
            if total_operation > 0:
                try:
                    mv = creer_mouvement_caisse(
                        montant=total_operation,
                        devise=devise_operation,
                        type_mouvement='ENTREE',
                        entreprise_id=sortie.entreprise_id,
                        succursale_id=sortie.succursale_id,
                        content_object=sortie,
                        sortie=sortie,
                        reference_piece=_vent_reference(sortie.pk, cle),
                        motif='',
                        utilisateur=utilisateur,
                        type_caisse=caisse_cible,
                    )
                except (CaisseError, SessionCaisseError) as exc:
                    raise _erreur_caisse(exc) from exc
                impacts.append(_impact(mv, 'ENCAISSEMENT'))
            continue

        par_caisse: dict[int | None, list[MouvementCaisse]] = {}
        for e in ecritures_cle:
            par_caisse.setdefault(e.type_caisse_id, []).append(e)
        cibles: dict[int | None, Decimal] = {caisse_id: Decimal('0') for caisse_id in par_caisse}
        taux_cible = None
        if total_operation > 0:
            reference = origine if origine and origine.type_caisse_id == caisse_cible.pk else None
            montant_cible, taux_cible = _montant_en_devise_caisse(
                total_operation, devise_operation, caisse_cible,
                entreprise_id=sortie.entreprise_id, reference=reference,
            )
            cibles[caisse_cible.pk] = montant_cible

        # Les sorties d'argent d'abord échouent tôt si le solde manque ; les entrées ensuite.
        for caisse_id, cible in sorted(cibles.items(), key=lambda item: item[1] - _net(par_caisse.get(item[0], []))):
            existantes = par_caisse.get(caisse_id, [])
            delta = cible - _net(existantes)
            if delta == 0:
                continue
            type_caisse = existantes[0].type_caisse if existantes else caisse_cible
            if (
                len(existantes) == 1
                and existantes[0] is origine
                and origine.type == 'ENTREE'
                and _modifiable_sur_place(origine)
            ):
                if delta < 0 and type_caisse is not None:
                    _verifier_solde(type_caisse, sortie.succursale_id, -delta)
                avant = _quantize(origine.montant)
                _corriger_sur_place(origine, cible, total_operation, devise_operation, taux_cible)
                impacts.append(_impact(origine, 'CORRECTION', avant=avant))
                continue
            if type_caisse is None:
                # Encaissement historique sans caisse : correction sur place uniquement.
                raise serializers.ValidationError({
                    'type_caisse_id': (
                        "L'encaissement d'origine de cette vente n'est rattaché à aucune caisse : "
                        "sélectionnez une caisse pour enregistrer l'ajustement."
                    ),
                })
            if delta < 0:
                _verifier_solde(type_caisse, sortie.succursale_id, -delta)
            prefixe = _ajustement_prefixe(sortie.pk, cle)
            numero = _prochain_numero_ajustement(ecritures, prefixe)
            try:
                mv = creer_mouvement_caisse(
                    montant=abs(delta),
                    devise=type_caisse.devise or devise_operation,
                    type_mouvement='ENTREE' if delta > 0 else 'SORTIE',
                    entreprise_id=sortie.entreprise_id,
                    succursale_id=sortie.succursale_id,
                    content_object=sortie,
                    sortie=sortie,
                    reference_piece=f'{prefixe}{numero}',
                    motif=f'Ajustement — {libelle}',
                    utilisateur=utilisateur,
                    type_caisse=type_caisse,
                    categorie='VENTE',
                )
            except (CaisseError, SessionCaisseError) as exc:
                raise _erreur_caisse(exc) from exc
            ecritures.append(mv)
            impacts.append(_impact(mv, 'AJUSTEMENT'))
    return impacts


def _impact(mv: MouvementCaisse, nature: str, *, avant: Decimal | None = None) -> dict:
    data = {
        'nature': nature,
        'mouvement_id': mv.pk,
        'reference_piece': mv.reference_piece,
        'type': mv.type,
        'montant': str(_quantize(mv.montant)),
        'devise': mv.devise.sigle if mv.devise else '',
        'caisse_id': mv.type_caisse_id,
        'caisse': mv.type_caisse.libelle_affiche if mv.type_caisse else '',
    }
    if avant is not None:
        data['montant_avant'] = str(avant)
    return data


def reverse_sortie_cash_movements(sortie: Sortie, *, utilisateur=None, motif: str = 'Passage vente en crédit') -> list[dict]:
    """Ramène à zéro l'encaissement net d'une sortie (crédit, sortie non commerciale)."""
    return sync_sortie_cash_movements(sortie, {}, utilisateur=utilisateur, motif_ajustement=motif)
