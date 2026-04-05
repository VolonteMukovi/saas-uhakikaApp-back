"""
Livraison commande : passage à « livrée » → sortie de stock (FIFO), comme une vente classique.

Même logique métier que ``SortieViewSet.create`` (lots, ``Stock``, ``BeneficeLot``, caisse).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from order.models import Commande
from stock.models import (
    BeneficeLot,
    Devise,
    LigneEntree,
    LigneSortie,
    LigneSortieLot,
    Sortie,
    Stock,
)
from stock.services.caisse import creer_mouvement_caisse


@transaction.atomic
def apply_sortie_on_commande_livree(commande: Commande) -> Sortie:
    """
    Crée une ``Sortie`` + lignes FIFO pour les articles de la commande, lie ``commande.sortie_livraison``.

    - Lignes sans article catalogue (``nom_article`` seul) : refusé.
    - Déjà livrée (``sortie_livraison`` renseignée) : refusé.
    """
    commande = (
        Commande.objects.select_for_update()
        .select_related("client", "entreprise", "succursale")
        .prefetch_related("items__article")
        .get(pk=commande.pk)
    )

    if commande.sortie_livraison_id:
        raise ValidationError(
            {
                "statut": _(
                    "Une sortie de stock est déjà liée à cette commande (livraison déjà enregistrée)."
                )
            }
        )

    items = list(commande.items.all())
    if not items:
        raise ValidationError(
            {"statut": _("La commande ne contient aucune ligne : impossible de livrer.")}
        )

    bad = [it for it in items if it.article_id is None]
    if bad:
        raise ValidationError(
            {
                "statut": _(
                    "Impossible de livrer : toutes les lignes doivent référencer un article du catalogue "
                    "(les lignes au nom libre seul ne génèrent pas de sortie de stock)."
                )
            }
        )

    tenant_id = commande.entreprise_id
    branch_id = commande.succursale_id

    default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
    if default_dev is None:
        default_dev = Devise.objects.filter(entreprise_id=tenant_id).first()

    motif = _("Livraison commande %(ref)s") % {
        "ref": (commande.reference or "").strip() or f"#{commande.pk}"
    }

    sortie = Sortie.objects.create(
        motif=motif,
        statut="PAYEE",
        client=commande.client,
        entreprise_id=tenant_id,
        succursale_id=branch_id,
    )

    totaux_par_devise: dict[str, dict] = {}

    for it in items:
        article_obj = it.article
        qte = int(it.quantite)
        if qte < 1:
            raise ValidationError({"statut": _("Quantité invalide sur une ligne de commande.")})

        stock_disponible = (
            LigneEntree.objects.filter(
                article=article_obj,
                quantite_restante__gt=0,
                entree__entreprise_id=tenant_id,
            ).aggregate(total=Sum("quantite_restante"))["total"]
            or 0
        )

        if stock_disponible < qte:
            raise ValidationError(
                {
                    "statut": _(
                        "Stock insuffisant pour livrer la commande — article %(art)s "
                        "(disponible: %(disp)s, demandé: %(dem)s)."
                    )
                    % {
                        "art": article_obj.nom_scientifique,
                        "disp": stock_disponible,
                        "dem": qte,
                    }
                }
            )

        devise_obj = default_dev
        if devise_obj is None:
            raise ValidationError(
                {
                    "statut": _(
                        "Aucune devise n'est configurée pour cette entreprise. "
                        "Ajoutez une devise avant de marquer la commande comme livrée."
                    )
                }
            )

        lots_disponibles = (
            LigneEntree.objects.filter(
                article=article_obj,
                quantite_restante__gt=0,
                entree__entreprise_id=tenant_id,
            )
            .select_related("entree")
            .order_by("date_entree", "id")
        )

        quantite_restante_a_sortir = qte
        lots_utilises_data = []
        total_prix_vente = Decimal("0.00")

        for lot in lots_disponibles:
            if quantite_restante_a_sortir <= 0:
                break
            quantite_a_prelever = min(lot.quantite_restante, quantite_restante_a_sortir)
            lots_utilises_data.append(
                {
                    "lot": lot,
                    "quantite": quantite_a_prelever,
                    "prix_achat": lot.prix_unitaire,
                    "prix_vente": lot.prix_vente,
                }
            )
            lot.quantite_restante -= quantite_a_prelever
            lot.save(update_fields=["quantite_restante"])
            quantite_restante_a_sortir -= quantite_a_prelever
            total_prix_vente += lot.prix_vente * Decimal(str(quantite_a_prelever))

        prix_vente_moyen_lots = (
            (total_prix_vente / Decimal(str(qte))).quantize(Decimal("0.01")) if qte > 0 else Decimal("0.00")
        )
        prix_unitaire_final = prix_vente_moyen_lots

        ligne_sortie = LigneSortie.objects.create(
            sortie=sortie,
            article=article_obj,
            quantite=qte,
            prix_unitaire=prix_unitaire_final,
            devise=devise_obj,
        )

        for lot_data in lots_utilises_data:
            lot = lot_data["lot"]
            qte_lot = lot_data["quantite"]
            prix_achat = lot_data["prix_achat"]
            prix_vente_lot = lot_data["prix_vente"]
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
                benefice_unitaire=benefice_unitaire.quantize(Decimal("0.01")),
                benefice_total=benefice_total.quantize(Decimal("0.01")),
            )

        montant_ligne = prix_unitaire_final * Decimal(str(qte))
        devise_key = devise_obj.sigle if devise_obj else "DEFAULT"
        if devise_key not in totaux_par_devise:
            totaux_par_devise[devise_key] = {"devise_obj": devise_obj, "total": Decimal("0.00")}
        totaux_par_devise[devise_key]["total"] += montant_ligne

        stock_obj, _created = Stock.objects.get_or_create(
            article=article_obj,
            defaults={"Qte": 0, "seuilAlert": 0},
        )
        stock_obj.Qte -= qte
        stock_obj.save(update_fields=["Qte"])

    for devise_key, devise_data in totaux_par_devise.items():
        devise_obj = devise_data["devise_obj"]
        total_devise = devise_data["total"]
        if total_devise > 0:
            ref_cmd = (commande.reference or "").strip() or str(commande.pk)
            piece = f"LIV-CMD-{ref_cmd}-{devise_key}"[:100]
            creer_mouvement_caisse(
                montant=total_devise.quantize(Decimal("0.01")),
                devise=devise_obj or default_dev,
                type_mouvement="ENTREE",
                entreprise_id=sortie.entreprise_id,
                succursale_id=sortie.succursale_id,
                content_object=sortie,
                sortie=sortie,
                reference_piece=piece,
                motif="",
            )

    commande.sortie_livraison = sortie
    commande.save(update_fields=["sortie_livraison"])

    return sortie
