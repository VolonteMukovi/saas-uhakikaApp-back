"""
Conversion inter-devises pour les mouvements de caisse.

Règle :
- ``montant`` / ``devise`` du mouvement = devise réelle de la caisse (après conversion).
- ``montant_origine`` / ``devise_origine`` = montant exprimé par l'opération métier.
- ``montant_reference`` / ``devise_reference`` = devise principale entreprise (rapports).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from caisse.models import TypeCaisse
from caisse.services.caisse_defaut import CaisseError
from stock.models import Devise
from stock.services.currency import (
    CurrencyError,
    build_conversion_snapshot,
    convert_amount,
    get_exchange_rate,
    quantize_amount,
    quantize_rate,
)


@dataclass
class CaisseConversionResult:
    """Résultat d'une préparation de mouvement caisse."""

    montant_caisse: Decimal
    devise_caisse: Devise
    montant_origine: Optional[Decimal]
    devise_origine: Optional[Devise]
    taux_conversion: Optional[Decimal]
    date_taux: datetime
    conversion_appliquee: bool
    devise_reference: Devise
    taux_reference: Decimal
    montant_reference: Decimal

    def to_dict(self) -> dict:
        return {
            'montant_operation': str(self.montant_origine if self.conversion_appliquee else self.montant_caisse),
            'devise_operation': {
                'id': (self.devise_origine or self.devise_caisse).pk,
                'sigle': (self.devise_origine or self.devise_caisse).sigle,
            },
            'montant_caisse': str(self.montant_caisse),
            'devise_caisse': {
                'id': self.devise_caisse.pk,
                'sigle': self.devise_caisse.sigle,
            },
            'montant_reference': str(self.montant_reference),
            'devise_reference': {
                'id': self.devise_reference.pk,
                'sigle': self.devise_reference.sigle,
            },
            'taux_conversion': str(self.taux_conversion) if self.taux_conversion is not None else None,
            'taux_reference': str(self.taux_reference),
            'date_taux': self.date_taux.isoformat(),
            'conversion_appliquee': self.conversion_appliquee,
        }


def _resolve_caisse_devise(type_caisse: TypeCaisse) -> Devise:
    if not type_caisse.devise_id:
        raise CaisseError('La caisse sélectionnée n\'a pas de devise configurée.')
    return type_caisse.devise


def convert_between_devises(
    amount,
    source_devise: Devise,
    target_devise: Devise,
    *,
    entreprise_id: int,
    date_operation=None,
    explicit_rate: Decimal | None = None,
) -> tuple[Decimal, Decimal, datetime]:
    """Convertit un montant ; retourne (montant_converti, taux, date_taux)."""
    amt = quantize_amount(amount)
    ref_date = date_operation or timezone.now()
    if source_devise.pk == target_devise.pk:
        return amt, Decimal('1.00000000'), ref_date
    rate = get_exchange_rate(
        source_devise,
        target_devise,
        entreprise_id=entreprise_id,
        date_operation=date_operation,
        explicit_rate=explicit_rate,
    )
    return convert_amount(amt, rate), quantize_rate(rate), ref_date


def prepare_caisse_movement(
    *,
    montant_operation: Decimal,
    devise_operation: Devise,
    type_caisse: TypeCaisse,
    entreprise_id: int,
    date_operation=None,
    explicit_conversion_rate: Decimal | None = None,
) -> CaisseConversionResult:
    """
    Prépare les montants pour un mouvement caisse.

    ``montant_operation`` est dans la devise de l'opération métier.
    Le résultat ``montant_caisse`` est dans la devise de la caisse.
    """
    if devise_operation is None:
        raise CaisseError('Devise requise pour un mouvement de caisse.')

    caisse_devise = _resolve_caisse_devise(type_caisse)
    montant_op = quantize_amount(montant_operation)
    ref_date = date_operation or timezone.now()

    if devise_operation.pk == caisse_devise.pk:
        montant_caisse = montant_op
        taux_conversion = None
        montant_origine = None
        devise_origine = None
        conversion_appliquee = False
    else:
        try:
            montant_caisse, taux_conversion, ref_date = convert_between_devises(
                montant_op,
                devise_operation,
                caisse_devise,
                entreprise_id=entreprise_id,
                date_operation=date_operation,
                explicit_rate=explicit_conversion_rate,
            )
        except CurrencyError as exc:
            raise CaisseError(
                f"Taux de change introuvable : impossible de convertir "
                f"{devise_operation.sigle} vers {caisse_devise.sigle}. {exc}"
            ) from exc
        montant_origine = montant_op
        devise_origine = devise_operation
        conversion_appliquee = True

    snapshot_source = devise_origine or caisse_devise
    snapshot_amount = montant_origine if montant_origine is not None else montant_caisse
    try:
        snapshot = build_conversion_snapshot(
            entreprise_id=entreprise_id,
            amount=snapshot_amount,
            devise_source=snapshot_source,
            date_operation=date_operation,
        )
    except CurrencyError as exc:
        raise CaisseError(str(exc)) from exc

    return CaisseConversionResult(
        montant_caisse=montant_caisse,
        devise_caisse=caisse_devise,
        montant_origine=montant_origine,
        devise_origine=devise_origine,
        taux_conversion=taux_conversion,
        date_taux=ref_date,
        conversion_appliquee=conversion_appliquee,
        devise_reference=snapshot['devise_reference'],
        taux_reference=snapshot['taux_change'],
        montant_reference=snapshot['montant_reference'],
    )


def payment_equivalent_in_dette_currency(
    montant_paye,
    devise_paiement: Devise,
    dette_devise: Devise,
    *,
    entreprise_id: int,
    date_operation=None,
    explicit_rate: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    """Montant du paiement exprimé dans la devise de la dette + taux utilisé."""
    equivalent, rate, _ = convert_between_devises(
        montant_paye,
        devise_paiement,
        dette_devise,
        entreprise_id=entreprise_id,
        date_operation=date_operation,
        explicit_rate=explicit_rate,
    )
    return equivalent, rate
