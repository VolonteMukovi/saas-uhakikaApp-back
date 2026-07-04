"""Ajustement des mouvements de caisse liés à une vente comptant."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from rest_framework import serializers

from caisse.models import MouvementCaisse
from caisse.services.caisse import creer_mouvement_caisse
from stock.models import Devise, Sortie
from stock.services.currency import build_conversion_snapshot


def _quantize(amount) -> Decimal:
    return Decimal(str(amount or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _vent_reference(sortie_id: int, devise_key: str) -> str:
    return f'VENT-{sortie_id}-{devise_key}'


@transaction.atomic
def reverse_sortie_cash_movements(sortie: Sortie, *, utilisateur=None, motif: str = 'Passage vente en crédit') -> None:
    """Annule les encaissements comptant d'une sortie (montant → 0, conserve la trace)."""
    mouvements = (
        MouvementCaisse.objects.select_for_update()
        .filter(sortie=sortie, type='ENTREE', reference_piece__startswith=f'VENT-{sortie.pk}-')
    )
    for mv in mouvements:
        mv.montant = Decimal('0')
        mv.montant_reference = Decimal('0')
        if motif:
            mv.motif = motif
        mv.save(update_fields=['montant', 'montant_reference', 'motif'])


@transaction.atomic
def sync_sortie_cash_movements(
    sortie: Sortie,
    totaux_par_devise: dict,
    *,
    utilisateur=None,
    type_caisse_id: int | None = None,
    old_statut: str | None = None,
    new_statut: str | None = None,
) -> None:
    """
    Synchronise les mouvements caisse d'une vente.

    - PAYEE : un seul mouvement ENTREE par devise (référence ``VENT-{pk}-{devise}``), montant mis à jour.
    - EN_CREDIT : aucun encaissement (montant 0 ou annulation des anciens mouvements).
    """
    sortie = Sortie.objects.select_for_update().get(pk=sortie.pk)
    new_statut = new_statut or sortie.statut
    old_statut = old_statut or sortie.statut

    if new_statut == 'EN_CREDIT':
        if old_statut == 'PAYEE':
            reverse_sortie_cash_movements(sortie, utilisateur=utilisateur, motif='Passage vente en crédit')
        return

    if old_statut == 'EN_CREDIT' and new_statut == 'PAYEE':
        encaissement_requis = any(_quantize(d['total']) > 0 for d in totaux_par_devise.values())
        if encaissement_requis and not type_caisse_id:
            raise serializers.ValidationError({'type_caisse_id': 'Type de caisse requis pour encaisser la vente.'})

    for devise_key, devise_data in totaux_par_devise.items():
        devise_obj = devise_data['devise_obj']
        total_devise = _quantize(devise_data['total'])
        ref = _vent_reference(sortie.pk, devise_key)

        mv = (
            MouvementCaisse.objects.select_for_update()
            .filter(sortie=sortie, reference_piece=ref)
            .first()
        )

        if total_devise <= 0:
            if mv:
                mv.montant = Decimal('0')
                mv.montant_reference = Decimal('0')
                mv.save(update_fields=['montant', 'montant_reference'])
            continue

        snapshot = build_conversion_snapshot(
            entreprise_id=sortie.entreprise_id,
            amount=total_devise,
            devise_source=devise_obj,
        )

        if mv:
            mv.montant = total_devise
            mv.devise = devise_obj
            mv.devise_reference = snapshot['devise_reference']
            mv.taux_change = snapshot['taux_change']
            mv.montant_reference = snapshot['montant_reference']
            if type_caisse_id and not mv.type_caisse_id:
                mv.type_caisse_id = type_caisse_id
            mv.save()
        else:
            if not type_caisse_id:
                raise serializers.ValidationError({'type_caisse_id': 'Type de caisse requis pour encaisser la vente.'})
            creer_mouvement_caisse(
                montant=total_devise,
                devise=devise_obj,
                type_mouvement='ENTREE',
                entreprise_id=sortie.entreprise_id,
                succursale_id=sortie.succursale_id,
                content_object=sortie,
                sortie=sortie,
                reference_piece=ref,
                motif='',
                utilisateur=utilisateur,
                type_caisse_id=type_caisse_id,
                devise_reference=snapshot['devise_reference'],
                taux_change=snapshot['taux_change'],
                montant_reference=snapshot['montant_reference'],
                skip_session_check=True,
            )
