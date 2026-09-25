"""Détail client — achats & dettes (logique simple).

Source de vérité :
- achats = Sortie (PAYEE + EN_CREDIT) + LigneSortie
- dette restante = somme(DettesClients.reste)
- PaiementDettesClients n'est jamais un achat
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

from stock.models import Client, ClientEntreprise, DettesClients, LigneSortie, Sortie

ZERO = Decimal("0.00000")
_MONEY_FIELD = DecimalField(max_digits=14, decimal_places=5)
_LINE_TOTAL = ExpressionWrapper(
    F("quantite") * F("prix_unitaire"),
    output_field=_MONEY_FIELD,
)


def _amount(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.00001"), rounding=ROUND_DOWN)


def _amount_str(value) -> str:
    return f"{_amount(value):.5f}"


def _period_lookup(qs, field_lookup: str, date_debut, date_fin):
    if date_debut:
        qs = qs.filter(**{f"{field_lookup}__gte": date_debut})
    if date_fin:
        qs = qs.filter(**{f"{field_lookup}__lte": date_fin})
    return qs


def parse_period_from_request(request):
    date_debut = request.query_params.get("date_debut")
    date_fin = request.query_params.get("date_fin")

    if date_debut:
        date_debut = timezone.datetime.strptime(date_debut, "%Y-%m-%d").date()
    if date_fin:
        date_fin = timezone.datetime.strptime(date_fin, "%Y-%m-%d").date()
    if date_debut and date_fin and date_debut > date_fin:
        raise ValueError("date_debut doit etre inferieure ou egale a date_fin.")

    mode = "tout"
    if date_debut and date_fin:
        mode = "periode_personnalisee"
    elif date_debut:
        mode = "depuis_le"
    elif date_fin:
        mode = "jusqu_au"

    return {
        "date_debut": date_debut.isoformat() if date_debut else None,
        "date_fin": date_fin.isoformat() if date_fin else None,
        "mode": mode,
        "_date_debut": date_debut,
        "_date_fin": date_fin,
    }


def _client_type(*, client: Client, entreprise_id: int) -> str:
    link = (
        ClientEntreprise.objects.filter(client=client, entreprise_id=entreprise_id)
        .only("is_special")
        .first()
    )
    if link and link.is_special:
        return "SPECIAL"
    return "STANDARD"


def _article_nom(article) -> str:
    if not article:
        return ""
    return article.nom_commercial or article.nom_scientifique or str(article.pk)


def _sorties_qs(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """Achats = sorties du client (date = date_creation de la sortie)."""
    qs = Sortie.objects.filter(client=client, entreprise_id=entreprise_id)
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)
    return _period_lookup(qs, "date_creation__date", period["_date_debut"], period["_date_fin"])


def _dettes_qs(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """Dettes filtrées sur DettesClients.date (pas la date de paiement)."""
    qs = DettesClients.objects.filter(
        sortie__client=client,
        sortie__entreprise_id=entreprise_id,
    )
    if succursale_id is not None:
        qs = qs.filter(sortie__succursale_id=succursale_id)
    return _period_lookup(qs, "date", period["_date_debut"], period["_date_fin"])


def _lignes_achats_qs(sorties_qs):
    return (
        LigneSortie.objects.filter(sortie__in=sorties_qs)
        .select_related("article", "devise", "sortie")
        .annotate(line_total=_LINE_TOTAL)
        .order_by("-sortie__date_creation", "-id")
    )


def build_produits_achetes(sorties_qs) -> list[dict]:
    """Lignes produit issues des sorties (jamais des paiements de dettes)."""
    results = []
    for ligne in _lignes_achats_qs(sorties_qs):
        qte = _amount(ligne.quantite)
        pu = _amount(ligne.prix_unitaire)
        dt = ligne.sortie.date_creation
        results.append(
            {
                "date": timezone.localtime(dt).date().isoformat() if dt else None,
                "produit": _article_nom(ligne.article),
                "article_id": ligne.article_id,
                "quantite": f"{qte:.5f}",
                "prix_unitaire": f"{pu:.5f}",
                "total": _amount_str(getattr(ligne, "line_total", qte * pu)),
                "devise": ligne.devise.sigle if ligne.devise_id else None,
                "sortie_id": ligne.sortie_id,
                "statut_vente": ligne.sortie.statut,
            }
        )
    return results


def build_client_dashboard(
    *,
    client: Client,
    entreprise_id: int,
    succursale_id: int | None,
    period: dict,
):
    """
    Réponse minimale pour le détail client :

    - nombre_achats : nb de Sortie (comptant + crédit)
    - total_achete : Σ (qté × PU) des LigneSortie
    - dette_restante : Σ DettesClients.reste (filtrées par date de dette)
    - produits_achetes : lignes produit
    """
    sorties = _sorties_qs(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    dettes = _dettes_qs(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )

    lignes = LigneSortie.objects.filter(sortie__in=sorties).annotate(line_total=_LINE_TOTAL)
    agg = lignes.aggregate(total=Sum("line_total"), nb_lignes=Count("id"))
    dette_agg = dettes.aggregate(
        montant=Sum("montant"),
        paye=Sum("paye"),
        reste=Sum("reste"),
    )

    produits = build_produits_achetes(sorties)

    return {
        "client": {
            "id": client.pk,
            "nom": client.nom,
            "telephone": client.telephone,
            "email": client.email,
            "adresse": client.adresse,
            "type": _client_type(client=client, entreprise_id=entreprise_id),
        },
        "periode": {
            "date_debut": period["date_debut"],
            "date_fin": period["date_fin"],
            "mode": period["mode"],
        },
        "nombre_achats": sorties.count(),
        "total_achete": _amount_str(agg["total"]),
        "dette_restante": _amount_str(dette_agg["reste"]),
        "situation_dettes": {
            "dette_totale": _amount_str(dette_agg["montant"]),
            "total_paye": _amount_str(dette_agg["paye"]),
            "reste": _amount_str(dette_agg["reste"]),
        },
        "produits_achetes": produits,
        "nombre_lignes_produits": agg["nb_lignes"] or 0,
    }


def build_client_statistics(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """Alias du dashboard simplifié (plus de KPIs secondaires)."""
    return build_client_dashboard(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )


def build_client_balance(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """Solde = dette restante uniquement (nouvelle logique DettesClients.reste)."""
    dashboard = build_client_dashboard(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    return {
        "client": dashboard["client"],
        "periode": dashboard["periode"],
        "dette_restante": dashboard["dette_restante"],
        "nombre_achats": dashboard["nombre_achats"],
        "total_achete": dashboard["total_achete"],
    }


def build_client_sales(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """Liste des achats (sorties) — hors paiements de dettes."""
    sorties = (
        _sorties_qs(
            client=client,
            entreprise_id=entreprise_id,
            succursale_id=succursale_id,
            period=period,
        )
        .annotate(
            montant_total=Sum(
                ExpressionWrapper(
                    F("lignes__quantite") * F("lignes__prix_unitaire"),
                    output_field=_MONEY_FIELD,
                )
            ),
            nombre_lignes=Count("lignes"),
        )
        .order_by("-date_creation", "-id")
    )
    results = []
    for sortie in sorties:
        results.append(
            {
                "id": sortie.pk,
                "date": sortie.date_creation.isoformat() if sortie.date_creation else None,
                "reference": f"SORTIE-{sortie.pk}",
                "type": "VENTE_COMPTANT" if sortie.statut == "PAYEE" else "VENTE_CREDIT",
                "statut": sortie.statut,
                "montant_total": _amount_str(sortie.montant_total),
                "nombre_lignes": sortie.nombre_lignes or 0,
                "motif": sortie.motif or "",
            }
        )
    return results


def build_client_movements(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """
    Remplace l'ancien journal débit/crédit/solde.

    Retourne les produits achetés (même source que dashboard.produits_achetes),
    paginables côté view.
    """
    sorties = _sorties_qs(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    return build_produits_achetes(sorties)
