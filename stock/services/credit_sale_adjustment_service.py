"""Ajustement de la dette liée à une vente à crédit."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers

from stock.models import DetteClient, Devise, Sortie
from stock.services.credit_sale_debt import (
    compute_sortie_line_total,
    create_dette_for_credit_sortie,
    resolve_sortie_primary_devise,
)
from stock.services.currency import build_conversion_snapshot


def _quantize(amount) -> Decimal:
    return Decimal(str(amount or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


@transaction.atomic
def sync_dette_for_credit_sortie(
    sortie: Sortie,
    *,
    default_devise: Devise | None = None,
    old_statut: str | None = None,
    new_statut: str | None = None,
) -> DetteClient | None:
    """
    Met à jour ou supprime la dette selon le statut de la sortie.

    - EN_CREDIT : recalcule montant_total, refuse si < montant déjà payé.
    - PAYEE : supprime la dette uniquement si aucun paiement enregistré.
    """
    sortie = Sortie.objects.select_for_update().get(pk=sortie.pk)
    new_statut = new_statut or sortie.statut
    old_statut = old_statut or sortie.statut

    dette = DetteClient.objects.select_for_update().filter(sortie=sortie).first()

    if new_statut != 'EN_CREDIT':
        if dette:
            montant_paye = dette.montant_paye
            if montant_paye > 0:
                raise serializers.ValidationError({
                    'statut': _(
                        'Impossible de passer en comptant : des paiements ont déjà été enregistrés sur cette dette.'
                    ),
                })
            dette.delete()
        return None

    if not sortie.client_id:
        raise serializers.ValidationError({'client_id': _('Client obligatoire pour une vente à crédit.')})

    new_total = compute_sortie_line_total(sortie)
    if new_total <= 0:
        raise serializers.ValidationError({'lignes': _('Impossible : montant de la vente nul.')})

    devise_dette = resolve_sortie_primary_devise(sortie, default_devise=default_devise)
    if devise_dette is None:
        raise serializers.ValidationError({'devise': _('Devise introuvable pour la vente à crédit.')})

    if not sortie.devise_id:
        sortie.devise = devise_dette
        sortie.save(update_fields=['devise'])

    snapshot = build_conversion_snapshot(
        entreprise_id=sortie.entreprise_id,
        amount=new_total,
        devise_source=devise_dette,
    )

    if not dette:
        if old_statut == 'PAYEE':
            return create_dette_for_credit_sortie(sortie, default_devise=default_devise, raise_if_exists=False)
        return create_dette_for_credit_sortie(sortie, default_devise=default_devise, raise_if_exists=True)

    montant_paye = dette.montant_paye
    if new_total < montant_paye:
        raise serializers.ValidationError({
            'lignes': _(
                'Modification impossible : le nouveau total de la vente ne peut pas être inférieur '
                'au montant déjà payé par le client.'
            ),
        })

    dette.montant_total = new_total
    dette.devise = devise_dette
    dette.devise_reference = snapshot['devise_reference']
    dette.taux_change = snapshot['taux_change']
    dette.montant_reference = snapshot['montant_reference']
    dette.client_id = sortie.client_id

    solde = new_total - montant_paye
    if solde <= 0:
        dette.statut = 'PAYEE'
    else:
        dette.statut = 'EN_COURS'
    dette.save()
    return dette
