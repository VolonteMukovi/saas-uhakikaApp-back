"""Logique simple DettesClients / PaiementDettesClients."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework import serializers

from stock.models import DettesClients, LigneSortie, PaiementDettesClients, Sortie

ZERO = Decimal("0.00000")
_Q = Decimal("0.00001")
_MONEY = DecimalField(max_digits=14, decimal_places=5)
_LINE_TOTAL = ExpressionWrapper(F("quantite") * F("prix_unitaire"), output_field=_MONEY)


def _q(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(_Q, rounding=ROUND_DOWN)


def calculer_montant_sortie(sortie: Sortie) -> Decimal:
    agg = LigneSortie.objects.filter(sortie=sortie).aggregate(total=Sum(_LINE_TOTAL))
    return _q(agg["total"])


def _as_date(value) -> date:
    if value is None:
        return timezone.localdate()
    if isinstance(value, datetime):
        return timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    if isinstance(value, date):
        return value
    try:
        return timezone.datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError(
            {"date": "Format de date invalide. Attendu : YYYY-MM-DD."}
        ) from exc


@transaction.atomic
def creer_dette_pour_sortie_credit(sortie: Sortie, *, date_dette=None) -> DettesClients:
    """Crée la dette pour une sortie EN_CREDIT (idempotent si déjà existante)."""
    if sortie.statut != "EN_CREDIT":
        raise serializers.ValidationError(
            {"statut": "Une dette n'est créée que pour une sortie EN_CREDIT."}
        )
    if not sortie.client_id:
        raise serializers.ValidationError(
            {"client": "Un client est obligatoire pour une vente à crédit."}
        )

    existing = DettesClients.objects.select_for_update().filter(sortie=sortie).first()
    if existing:
        return existing

    montant = calculer_montant_sortie(sortie)
    if montant <= 0:
        raise serializers.ValidationError(
            {"montant": "Le montant de la dette doit être supérieur à 0."}
        )

    d = _as_date(date_dette) if date_dette is not None else _as_date(sortie.date_creation)
    return DettesClients.objects.create(
        sortie=sortie,
        montant=montant,
        paye=ZERO,
        reste=montant,
        date=d,
        status=DettesClients.STATUS_ENCOURS,
    )


@transaction.atomic
def synchroniser_dette_sortie(sortie: Sortie) -> DettesClients | None:
    """
    Après mise à jour d'une sortie :
    - EN_CREDIT → crée ou met à jour le montant (si aucun paiement)
    - sinon → refuse la suppression si des paiements existent, sinon efface la dette
    """
    dette = DettesClients.objects.filter(sortie=sortie).select_for_update().first()

    if sortie.statut == "EN_CREDIT":
        if not sortie.client_id:
            raise serializers.ValidationError(
                {"client": "Un client est obligatoire pour une vente à crédit."}
            )
        if dette is None:
            return creer_dette_pour_sortie_credit(sortie)
        if dette.paiements.exists():
            return dette
        montant = calculer_montant_sortie(sortie)
        if montant <= 0:
            raise serializers.ValidationError(
                {"montant": "Le montant de la dette doit être supérieur à 0."}
            )
        dette.montant = montant
        dette.paye = ZERO
        dette.reste = montant
        dette.status = DettesClients.STATUS_ENCOURS
        dette.save(update_fields=["montant", "paye", "reste", "status", "updated_at"])
        return dette

    if dette is not None:
        if dette.paiements.exists() or dette.paye > 0:
            raise serializers.ValidationError(
                {
                    "statut": (
                        "Impossible de retirer le crédit : des paiements existent déjà "
                        "sur la dette liée à cette sortie."
                    )
                }
            )
        dette.delete()
    return None


@transaction.atomic
def enregistrer_paiement(
    dette: DettesClients,
    *,
    montant,
    date_paiement=None,
) -> PaiementDettesClients:
    """Enregistre un paiement partiel ou total et recalcule paye / reste / status."""
    dette = DettesClients.objects.select_for_update().get(pk=dette.pk)

    if dette.status == DettesClients.STATUS_TERMINE or dette.reste <= 0:
        raise serializers.ValidationError(
            {"dettes_clients": "Cette dette est terminée et ne peut plus recevoir de paiement."}
        )

    montant_paye = _q(montant)
    if montant_paye <= 0:
        raise serializers.ValidationError({"montant": "Le montant du paiement doit être supérieur à 0."})
    if montant_paye > dette.reste:
        raise serializers.ValidationError(
            {
                "montant": (
                    f"Le paiement ({montant_paye}) ne peut pas dépasser le reste dû ({dette.reste})."
                )
            }
        )

    paiement = PaiementDettesClients.objects.create(
        dettes_clients=dette,
        montant=montant_paye,
        date=_as_date(date_paiement),
    )
    # Mise à jour incrémentale sous verrou (évite un 2e SUM SQL inutile)
    dette.paye = _q(dette.paye) + montant_paye
    dette.reste = _q(dette.montant) - dette.paye
    if dette.reste < 0:
        dette.reste = ZERO
    dette.status = (
        DettesClients.STATUS_TERMINE if dette.reste == 0 else DettesClients.STATUS_ENCOURS
    )
    dette.save(update_fields=["paye", "reste", "status", "updated_at"])
    paiement.dettes_clients = dette
    return paiement


def filter_dettes_qs(qs, *, date_debut=None, date_fin=None, status=None, client_id=None):
    if date_debut:
        qs = qs.filter(date__gte=_as_date(date_debut))
    if date_fin:
        qs = qs.filter(date__lte=_as_date(date_fin))
    if status:
        st = str(status).upper().strip()
        if st not in (DettesClients.STATUS_ENCOURS, DettesClients.STATUS_TERMINE):
            raise serializers.ValidationError(
                {"status": "Statut invalide. Valeurs : ENCOURS, TERMINE."}
            )
        qs = qs.filter(status=st)
    if client_id:
        qs = qs.filter(sortie__client_id=client_id)
    return qs


def totaux_resume(qs) -> dict:
    """Une seule requête : total_reste + compteurs status."""
    agg = qs.aggregate(
        total_reste=Sum("reste"),
        nombre_dettes=Count("id"),
        nombre_encours=Count("id", filter=Q(status=DettesClients.STATUS_ENCOURS)),
        nombre_termine=Count("id", filter=Q(status=DettesClients.STATUS_TERMINE)),
    )
    return {
        "total_reste": f"{_q(agg['total_reste']):.5f}",
        "nombre_dettes": agg["nombre_dettes"] or 0,
        "nombre_encours": agg["nombre_encours"] or 0,
        "nombre_termine": agg["nombre_termine"] or 0,
    }


def totaux_reste(qs) -> Decimal:
    return _q(qs.aggregate(t=Sum("reste"))["t"])


def _devises_par_client(qs) -> dict[str, str | None]:
    """Une requête : sigle devise par client (sortie.devise, sinon ligne)."""
    from stock.models import LigneSortie

    # Priorité : devise portée par la Sortie
    rows_sortie = (
        qs.filter(sortie__client_id__isnull=False)
        .exclude(sortie__devise__sigle__isnull=True)
        .exclude(sortie__devise__sigle="")
        .values_list("sortie__client_id", "sortie__devise__sigle")
        .distinct()
    )
    by_client: dict[str, set[str]] = {}
    for client_id, sigle in rows_sortie:
        by_client.setdefault(client_id, set()).add(sigle)

    missing = set(
        qs.filter(sortie__client_id__isnull=False)
        .values_list("sortie__client_id", flat=True)
        .distinct()
    ) - set(by_client.keys())
    if missing:
        sortie_ids = qs.filter(sortie__client_id__in=missing).values_list("sortie_id", flat=True)
        rows_lignes = (
            LigneSortie.objects.filter(sortie_id__in=sortie_ids, sortie__client_id__in=missing)
            .exclude(devise__sigle__isnull=True)
            .exclude(devise__sigle="")
            .values_list("sortie__client_id", "devise__sigle")
            .distinct()
        )
        for client_id, sigle in rows_lignes:
            by_client.setdefault(client_id, set()).add(sigle)

    return {
        cid: (sorted(sigles)[0] if sigles else None)
        for cid, sigles in by_client.items()
    }


def totaux_par_client_qs(qs, *, only_positif: bool = True):
    """ValuesQuerySet paginable (CURSOR.md) — ne matérialise pas toute la table."""
    rows = (
        qs.filter(sortie__client__isnull=False)
        .values("sortie__client_id", "sortie__client__nom")
        .annotate(total_reste=Sum("reste"))
        .order_by("sortie__client__nom", "sortie__client_id")
    )
    if only_positif:
        rows = rows.filter(total_reste__gt=0)
    return rows


def enrichir_clients_devise(dettes_qs, rows) -> list[dict]:
    """Ajoute devise_sigle aux lignes client déjà paginées (1 requête devises)."""
    client_ids = [r["sortie__client_id"] for r in rows]
    devises = _devises_par_client(dettes_qs.filter(sortie__client_id__in=client_ids)) if client_ids else {}
    results = []
    for r in rows:
        cid = r["sortie__client_id"]
        results.append(
            {
                "client_id": cid,
                "client_nom": r["sortie__client__nom"],
                "total_reste": f"{_q(r['total_reste']):.5f}",
                "devise_sigle": devises.get(cid),
            }
        )
    return results


def totaux_par_client(qs, *, only_positif: bool = True):
    """Compat : liste + total (préférer totaux_par_client_qs + pagination en vue)."""
    rows = list(totaux_par_client_qs(qs, only_positif=only_positif))
    clients = enrichir_clients_devise(qs, rows)
    return clients, totaux_reste(qs)
