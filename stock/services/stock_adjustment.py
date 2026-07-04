"""Ajustements stock / lots pour entrées et sorties."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from stock.models import Article, BeneficeLot, LigneEntree, LigneSortie, LigneSortieLot, Stock


def quantize_qty(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def quantite_vendue_ligne_entree(ligne: LigneEntree) -> Decimal:
    return quantize_qty(ligne.quantite) - quantize_qty(ligne.quantite_restante)


def apply_stock_delta(article: Article, delta: Decimal, *, seuil_alerte: Decimal | None = None) -> Stock:
    stock_obj, _ = Stock.objects.select_for_update().get_or_create(
        article=article,
        defaults={'Qte': Decimal('0'), 'seuilAlert': seuil_alerte or Decimal('0')},
    )
    stock_obj.Qte = quantize_qty(stock_obj.Qte) + quantize_qty(delta)
    if seuil_alerte is not None:
        stock_obj.seuilAlert = seuil_alerte
    stock_obj.save(update_fields=['Qte', 'seuilAlert'])
    return stock_obj


def validate_ligne_entree_can_reduce(ligne: LigneEntree, new_quantite: Decimal) -> None:
    vendue = quantite_vendue_ligne_entree(ligne)
    new_q = quantize_qty(new_quantite)
    if new_q < vendue:
        article_nom = ligne.article.nom_scientifique if ligne.article_id else str(ligne.article_id)
        disponible = quantize_qty(ligne.quantite_restante)
        raise serializers.ValidationError({
            'quantite': (
                f"Modification impossible pour « {article_nom} » : une partie du stock a déjà été vendue. "
                f"Quantité minimale autorisée : {vendue}. Stock encore disponible sur ce lot : {disponible}."
            ),
        })


def validate_ligne_entree_can_delete(ligne: LigneEntree) -> None:
    vendue = quantite_vendue_ligne_entree(ligne)
    if vendue > 0:
        article_nom = ligne.article.nom_scientifique if ligne.article_id else str(ligne.article_id)
        raise serializers.ValidationError({
            'lignes_supprimees': (
                f"Impossible de supprimer la ligne de « {article_nom} » : "
                f"{vendue} unité(s) ont déjà été vendues depuis cet approvisionnement."
            ),
        })


@transaction.atomic
def remove_ligne_entree_from_stock(ligne: LigneEntree) -> None:
    ligne = LigneEntree.objects.select_for_update().get(pk=ligne.pk)
    validate_ligne_entree_can_delete(ligne)
    apply_stock_delta(ligne.article, -quantize_qty(ligne.quantite))
    ligne.delete()


def stock_disponible_article(article: Article) -> Decimal:
    total = (
        LigneEntree.objects.filter(article=article, quantite_restante__gt=0)
        .aggregate(total=Sum('quantite_restante'))['total']
    )
    return quantize_qty(total or 0)


def rollback_sortie_ligne(ligne: LigneSortie) -> None:
    for lot_utilise in ligne.lots_utilises.select_related('lot_entree').all():
        lot = LigneEntree.objects.select_for_update().get(pk=lot_utilise.lot_entree_id)
        lot.quantite_restante = quantize_qty(lot.quantite_restante) + quantize_qty(lot_utilise.quantite)
        lot.save(update_fields=['quantite_restante'])
    BeneficeLot.objects.filter(ligne_sortie=ligne).delete()
    ligne.lots_utilises.all().delete()
    apply_stock_delta(ligne.article, quantize_qty(ligne.quantite))
    ligne.delete()


def consume_fifo_lots(article: Article, quantite: Decimal) -> list[dict]:
    """Consomme les lots FIFO et retourne les données de traçabilité."""
    qte = quantize_qty(quantite)
    lots_disponibles = (
        LigneEntree.objects.select_for_update()
        .filter(article=article, quantite_restante__gt=0)
        .order_by('date_entree', 'id')
    )
    quantite_restante_a_sortir = qte
    lots_utilises_data = []
    total_prix_vente = Decimal('0')

    for lot in lots_disponibles:
        if quantite_restante_a_sortir <= 0:
            break
        quantite_a_prelever = min(quantize_qty(lot.quantite_restante), quantite_restante_a_sortir)
        lots_utilises_data.append({
            'lot': lot,
            'quantite': quantite_a_prelever,
            'prix_achat': lot.prix_unitaire,
            'prix_vente': lot.prix_vente,
        })
        lot.quantite_restante = quantize_qty(lot.quantite_restante) - quantite_a_prelever
        lot.save(update_fields=['quantite_restante'])
        quantite_restante_a_sortir -= quantite_a_prelever
        total_prix_vente += lot.prix_vente * quantite_a_prelever

    if quantite_restante_a_sortir > 0:
        disponible = stock_disponible_article(article)
        raise serializers.ValidationError(
            f"Stock insuffisant pour l'article {article.nom_scientifique} "
            f"(Disponible: {disponible}, Demandé: {qte})"
        )
    return lots_utilises_data, total_prix_vente


def create_sortie_lot_traces(ligne_sortie: LigneSortie, lots_utilises_data: list[dict], prix_unitaire_final: Decimal) -> None:
    for lot_data in lots_utilises_data:
        lot = lot_data['lot']
        qte_lot = lot_data['quantite']
        prix_achat = lot_data['prix_achat']
        prix_vente_lot = lot_data['prix_vente']
        LigneSortieLot.objects.create(
            ligne_sortie=ligne_sortie,
            lot_entree=lot,
            quantite=qte_lot,
            prix_achat=prix_achat,
            prix_vente=prix_vente_lot,
        )
        benefice_unitaire = prix_unitaire_final - prix_achat
        benefice_total = benefice_unitaire * Decimal(str(qte_lot))
        BeneficeLot.objects.create(
            lot_entree=lot,
            ligne_sortie=ligne_sortie,
            quantite_vendue=qte_lot,
            prix_achat=prix_achat,
            prix_vente=prix_unitaire_final,
            benefice_unitaire=benefice_unitaire.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
            benefice_total=benefice_total.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
        )
