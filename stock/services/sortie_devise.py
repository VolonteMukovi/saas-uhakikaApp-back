"""Helpers devise / montant pour les sorties (sans logique dette)."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db.models import DecimalField, ExpressionWrapper, F, Sum

from stock.models import Devise, LigneSortie, Sortie

_LINE_TOTAL = ExpressionWrapper(
    F('quantite') * F('prix_unitaire'),
    output_field=DecimalField(max_digits=14, decimal_places=5),
)


def compute_sortie_line_total(sortie: Sortie) -> Decimal:
    agg = LigneSortie.objects.filter(sortie=sortie).aggregate(total=Sum(_LINE_TOTAL))
    return Decimal(str(agg['total'] or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def resolve_sortie_primary_devise(sortie: Sortie, *, default_devise: Devise | None = None) -> Devise | None:
    if sortie.devise_id:
        return sortie.devise
    ligne = (
        LigneSortie.objects.filter(sortie=sortie, devise__isnull=False)
        .select_related('devise')
        .order_by('id')
        .first()
    )
    if ligne and ligne.devise_id:
        return ligne.devise
    if default_devise:
        return default_devise
    if sortie.entreprise_id:
        return Devise.objects.filter(entreprise_id=sortie.entreprise_id, est_principal=True).first()
    return None
