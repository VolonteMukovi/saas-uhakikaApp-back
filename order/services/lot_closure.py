"""
Clôture de lot : entrée en stock uniquement (pas d’impact caisse).

Les champs prix de vente / seuil / expiration ne sont pas stockés sur LotItem : ils viennent
du payload `approvisionnement` à la clôture et sont écrits sur LigneEntree uniquement.

Règle métier : l’approvisionnement issu d’un lot clôturé ne débite pas la caisse, ne vérifie pas
les soldes et utilise un libellé d’entrée imposé.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django.db import transaction
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from order.models import Lot, LotItem
from stock.models import Devise, Entree, LigneEntree, Stock


def entree_is_from_lot_closure(entree) -> bool:
    """True si cette entrée a été créée à la clôture d’un lot (lien Lot.entree_stock)."""
    if entree is None or not getattr(entree, "pk", None):
        return False
    return Lot.objects.filter(entree_stock_id=entree.pk).exists()


@dataclass
class _ClosureLine:
    lot_item: LotItem
    prix_vente: Decimal
    seuil_alerte: Decimal
    date_expiration: Any  # date | None


def _build_closure_lines(items: list[LotItem], approvisionnement: list[dict]) -> list[_ClosureLine]:
    if not items:
        raise ValidationError(
            {
                "statut": _(
                    "Impossible de clôturer un lot sans ligne d'article. "
                    "Ajoutez au moins un article au lot."
                )
            }
        )
    if not approvisionnement:
        raise ValidationError(
            {
                "approvisionnement": _(
                    "Veuillez compléter les informations d'approvisionnement "
                    "(prix de vente, seuil d'alerte, etc.) avant de clôturer le lot."
                )
            }
        )

    by_article = {row.article.article_id: row for row in items}
    seen: set[str] = set()
    out: list[_ClosureLine] = []
    for row in approvisionnement:
        aid = row["article_id"]
        if aid in seen:
            raise ValidationError(
                {"approvisionnement": _("L'article %(a)s est présent plusieurs fois dans le payload.") % {"a": aid}}
            )
        seen.add(aid)
        if aid not in by_article:
            raise ValidationError(
                {
                    "approvisionnement": _(
                        "L'article %(a)s ne figure pas dans ce lot. "
                        "Fournissez exactement une ligne par article du lot."
                    )
                    % {"a": aid}
                }
            )
        li = by_article[aid]
        pv = row["prix_vente"]
        sa = row["seuil_alerte"]
        de = row.get("date_expiration")
        try:
            pv_d = pv if isinstance(pv, Decimal) else Decimal(str(pv))
        except (InvalidOperation, TypeError, ValueError):
            pv_d = Decimal("0")
        if pv_d <= 0:
            raise ValidationError(
                {
                    "detail": _(
                        "Veuillez compléter les informations d'approvisionnement "
                        "(prix de vente, seuil d'alerte, etc.) avant de clôturer le lot."
                    ),
                    "approvisionnement": _("Le prix de vente doit être supérieur à 0 pour l'article %s.") % aid,
                }
            )
        try:
            sa_d = sa if isinstance(sa, Decimal) else Decimal(str(sa).replace(",", "."))
        except (TypeError, ValueError, InvalidOperation):
            raise ValidationError(
                {
                    "approvisionnement": _("Seuil d'alerte invalide pour l'article %s.") % aid,
                }
            )
        if sa_d < 0:
            raise ValidationError(
                {"approvisionnement": _("Le seuil d'alerte doit être positif ou nul pour l'article %s.") % aid}
            )
        out.append(_ClosureLine(lot_item=li, prix_vente=pv_d, seuil_alerte=sa_d, date_expiration=de))

    if seen != set(by_article.keys()):
        missing = set(by_article.keys()) - seen
        raise ValidationError(
            {
                "approvisionnement": _(
                    "Une ligne d'approvisionnement est requise pour chaque article du lot. "
                    "Manquants : %(ids)s"
                )
                % {"ids": ", ".join(sorted(missing))}
            }
        )

    return out


@transaction.atomic
def apply_stock_on_lot_closure(lot: Lot, approvisionnement: list[dict]) -> Entree:
    """
    Crée une entrée de stock, met à jour les quantités, relie le lot à cette entrée.

    Aucun mouvement de caisse ni contrôle de solde : coût d’achat déjà engagé hors caisse
    (lot en transit). ``approvisionnement`` : une entrée par article (article_id, prix_vente,
    seuil_alerte, date_expiration optionnelle).
    """
    lot = Lot.objects.select_for_update().select_related("entreprise", "succursale").get(pk=lot.pk)
    if lot.entree_stock_id:
        raise ValidationError(
            {"statut": _("Le stock pour ce lot a déjà été appliqué (entrée #%s).") % lot.entree_stock_id}
        )

    items = list(LotItem.objects.filter(lot_id=lot.pk).select_related("article"))
    lines = _build_closure_lines(items, approvisionnement)

    tenant_id = lot.entreprise_id
    branch_id = lot.succursale_id

    default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
    if default_dev is None:
        default_dev = Devise.objects.filter(entreprise_id=tenant_id).first()
    if default_dev is None:
        has_cost = any(
            Decimal(str(cl.lot_item.quantite)) * Decimal(str(cl.lot_item.prix_achat_unitaire)) > 0
            for cl in lines
        )
        if has_cost:
            raise ValidationError(
                {
                    "non_field_errors": _(
                        "Aucune devise n'est configurée pour cette entreprise. "
                        "Ajoutez au moins une devise avant de clôturer le lot."
                    )
                }
            )

    # Libellé imposé (traduit) — max 100 car. sur Entree.libele
    libele = force_str(_("Approvisionnement issu du lot (initialement en transit, maintenant arrivé)"))[:100]

    entree = Entree.objects.create(
        libele=libele,
        description="",
        entreprise_id=tenant_id,
        succursale_id=branch_id,
    )

    for cl in lines:
        row = cl.lot_item
        article_obj = row.article
        qte = row.quantite
        prix_unitaire = Decimal(str(row.prix_achat_unitaire))
        prix_vente = cl.prix_vente
        seuil_alerte = cl.seuil_alerte
        date_expiration = cl.date_expiration
        devise_obj = default_dev

        LigneEntree.objects.create(
            entree=entree,
            article=article_obj,
            quantite=qte,
            quantite_restante=qte,
            prix_unitaire=prix_unitaire,
            prix_vente=prix_vente,
            date_expiration=date_expiration,
            devise=devise_obj,
            seuil_alerte=seuil_alerte,
        )

        stock_obj, _created = Stock.objects.get_or_create(
            article=article_obj,
            defaults={"Qte": 0, "seuilAlert": seuil_alerte},
        )
        stock_obj.Qte += qte
        stock_obj.seuilAlert = seuil_alerte
        stock_obj.save()

    lot.entree_stock = entree
    lot.save(update_fields=["entree_stock"])

    return entree
