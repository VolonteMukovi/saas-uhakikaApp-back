from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from rest_framework import serializers

from stock.models import (
    Article,
    ConditionnementArticle,
    Devise,
    LigneEntree,
    PrixConditionnementEntree,
    TarifVente,
)
from stock.services.currency import convert_amount, get_exchange_rate, get_principal_devise


PRICE_QUANTIZER = Decimal('0.00001')


def convert_sale_price(
    amount: Decimal,
    source: Devise | None,
    target: Devise | None,
    *,
    entreprise_id: int,
) -> Decimal:
    source_devise = source or get_principal_devise(entreprise_id)
    if source_devise is None or target is None:
        raise serializers.ValidationError({'devise_id': 'Une devise valide est requise pour le prix de vente.'})
    rate = get_exchange_rate(source_devise, target, entreprise_id=entreprise_id)
    return convert_amount(amount, rate)


def get_fifo_lot_sale_price(
    lot: LigneEntree,
    conditionnement: ConditionnementArticle | None,
) -> tuple[Decimal, Devise | None]:
    if conditionnement is not None:
        specific_price = (
            PrixConditionnementEntree.objects
            .filter(ligne_entree=lot, conditionnement=conditionnement)
            .select_related('devise')
            .order_by('-est_prix_principal', 'id')
            .first()
        )
        if specific_price is not None:
            multiplier = Decimal(str(conditionnement.multiplicateur_base or '1'))
            if multiplier <= 0:
                raise serializers.ValidationError({
                    'conditionnement_id': 'Multiplicateur conditionnement invalide.',
                })
            unit_price = (specific_price.prix_vente / multiplier).quantize(
                PRICE_QUANTIZER,
                rounding=ROUND_DOWN,
            )
            return unit_price, specific_price.devise or lot.devise
    return lot.prix_vente_unitaire_base or lot.prix_vente, lot.devise


def get_fifo_lot_conditionnement_price(
    lot: LigneEntree,
    conditionnement: ConditionnementArticle | None,
) -> tuple[Decimal, Devise | None]:
    """Return the FIFO reference price in the requested package, without unit-rounding drift."""
    if conditionnement is None:
        return get_fifo_lot_sale_price(lot, None)
    multiplier = Decimal(str(conditionnement.multiplicateur_base or '1'))
    if multiplier <= 0:
        raise serializers.ValidationError({
            'conditionnement_id': 'Multiplicateur conditionnement invalide.',
        })
    specific_price = (
        PrixConditionnementEntree.objects
        .filter(ligne_entree=lot, conditionnement=conditionnement)
        .select_related('devise')
        .order_by('-est_prix_principal', 'id')
        .first()
    )
    if specific_price is not None:
        return specific_price.prix_vente, specific_price.devise or lot.devise
    unit_price, currency = get_fifo_lot_sale_price(lot, conditionnement)
    return (unit_price * multiplier).quantize(PRICE_QUANTIZER, rounding=ROUND_DOWN), currency


def get_tarif_vente_price(
    article: Article,
    conditionnement: ConditionnementArticle | None,
) -> tuple[Decimal, Devise] | None:
    """Return a configured article/pack tariff, falling back to its base-unit tariff."""
    tariff = (
        TarifVente.objects.filter(article=article, conditionnement=conditionnement)
        .select_related('devise')
        .first()
    )
    if tariff is not None:
        return tariff.prix, tariff.devise
    if conditionnement is None:
        return None
    base_tariff = (
        TarifVente.objects.filter(article=article, conditionnement__isnull=True)
        .select_related('devise')
        .first()
    )
    if base_tariff is None:
        return None
    multiplier = Decimal(str(conditionnement.multiplicateur_base or '1'))
    if multiplier <= 0:
        raise serializers.ValidationError({
            'conditionnement_id': 'Multiplicateur conditionnement invalide.',
        })
    return (
        (base_tariff.prix * multiplier).quantize(PRICE_QUANTIZER, rounding=ROUND_DOWN),
        base_tariff.devise,
    )


def normalize_fifo_lot_prices(
    lots_utilises_data: list[dict],
    conditionnement: ConditionnementArticle | None,
    devise_vente: Devise,
    *,
    entreprise_id: int,
) -> list[dict]:
    """Normalize FIFO retail and acquisition costs into the line's sale currency."""
    normalized = []
    for lot_data in lots_utilises_data:
        lot = lot_data['lot']
        sale_price, sale_currency = get_fifo_lot_sale_price(lot, conditionnement)
        cost_price = lot.prix_achat_unitaire_base or lot.prix_unitaire
        normalized.append({
            **lot_data,
            'prix_vente': convert_sale_price(
                sale_price,
                sale_currency or lot.devise,
                devise_vente,
                entreprise_id=entreprise_id,
            ),
            'prix_achat': convert_sale_price(
                cost_price,
                lot.devise,
                devise_vente,
                entreprise_id=entreprise_id,
            ),
        })
    return normalized


def validate_sale_price_policy(
    prix_unitaire: Decimal,
    quantite_base: Decimal,
    lots_utilises_data: list[dict],
    utilisateur,
    motif: str,
    *,
    montant_total: Decimal | None = None,
    request=None,
) -> str:
    total_cost = sum(
        (Decimal(str(lot_data['prix_achat'])) * Decimal(str(lot_data['quantite']))
         for lot_data in lots_utilises_data),
        Decimal('0'),
    )
    sale_total = montant_total if montant_total is not None else prix_unitaire * quantite_base
    is_free = sale_total <= 0
    below_cost = sale_total < total_cost
    reason = str(motif or '').strip()
    if len(reason) > 500:
        raise serializers.ValidationError({
            'motif_prix_exception': 'Le motif ne peut pas dépasser 500 caractères.',
        })
    if is_free or below_cost:
        is_admin = bool(
            utilisateur
            and (
                getattr(utilisateur, 'is_superuser', False)
                or (hasattr(utilisateur, 'is_admin') and utilisateur.is_admin(request))
            )
        )
        if not is_admin:
            raise serializers.ValidationError({
                'prix_unitaire': 'Seul un administrateur peut autoriser une vente gratuite ou sous le coût.',
            })
        if not reason:
            raise serializers.ValidationError({
                'motif_prix_exception': 'Un motif est obligatoire pour une vente gratuite ou sous le coût.',
            })
    return reason
