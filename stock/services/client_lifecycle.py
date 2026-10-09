"""Détail client — achats & dettes (logique simple).

Source de vérité :
- achats = Sortie (PAYEE + EN_CREDIT) + LigneSortie
- dette restante = somme(DettesClients.reste)
- PaiementDettesClients n'est jamais un achat
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Sum, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from stock.models import Client, ClientEntreprise, DettesClients, LigneSortie, Sortie

ZERO = Decimal("0.00000")
_MONEY_FIELD = DecimalField(max_digits=14, decimal_places=5)
_LINE_TOTAL = ExpressionWrapper(
    Coalesce(
        F("montant_total"),
        ExpressionWrapper(F("quantite") * F("prix_unitaire"), output_field=_MONEY_FIELD),
    ),
    output_field=_MONEY_FIELD,
)
_LINE_REFERENCE_TOTAL = Case(
    When(devise_reference__isnull=False, then=F("montant_reference")),
    default=_LINE_TOTAL,
    output_field=_MONEY_FIELD,
)
_SORTIE_LINE_REFERENCE_TOTAL = Case(
    When(lignes__devise_reference__isnull=False, then=F("lignes__montant_reference")),
    default=ExpressionWrapper(
        Coalesce(
            F("lignes__montant_total"),
            ExpressionWrapper(
                F("lignes__quantite") * F("lignes__prix_unitaire"),
                output_field=_MONEY_FIELD,
            ),
        ),
        output_field=_MONEY_FIELD,
    ),
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
        .select_related("article", "devise", "devise_reference", "sortie")
        .annotate(line_total=_LINE_TOTAL)
        .annotate(line_total_reference=_LINE_REFERENCE_TOTAL)
        .order_by("-sortie__date_creation", "-id")
    )


def build_produits_achetes(sorties_qs, *, devise_principale=None) -> list[dict]:
    """Lignes produit issues des sorties (jamais des paiements de dettes)."""
    results = []
    for ligne in _lignes_achats_qs(sorties_qs).iterator(chunk_size=200):
        qte = _amount(ligne.quantite)
        pu = _amount(ligne.prix_unitaire)
        total_origine = _amount(getattr(ligne, "line_total", qte * pu))
        total_reference = _amount(
            getattr(ligne, "line_total_reference", total_origine)
        )
        devise_reference = ligne.devise_reference
        devise_affichee = devise_reference or devise_principale or ligne.devise
        prix_unitaire_reference = (
            total_reference / qte if qte else pu
        )
        dt = ligne.sortie.date_creation
        if dt is not None:
            date_str = timezone.localtime(dt).date().isoformat() if timezone.is_aware(dt) else dt.date().isoformat()
        else:
            date_str = None
        results.append(
            {
                "date": date_str,
                "produit": _article_nom(ligne.article),
                "article_id": ligne.article_id,
                "quantite": f"{qte:.5f}",
                "prix_unitaire": _amount_str(prix_unitaire_reference),
                "total": _amount_str(total_reference),
                "devise": devise_affichee.sigle if devise_affichee else None,
                "prix_unitaire_origine": f"{pu:.5f}",
                "total_origine": f"{total_origine:.5f}",
                "devise_origine": ligne.devise.sigle if ligne.devise_id else None,
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
    include_produits: bool = True,
):
    """
    Réponse minimale pour le détail client :

    - nombre_achats : nb de Sortie (comptant + crédit)
    - total_achete : Σ (qté × PU) des LigneSortie
    - dette_restante : Σ DettesClients.reste (filtrées par date de dette)
    - produits_achetes : lignes produit (optionnel pour alléger /solde)
    """
    sorties = _sorties_qs(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    from stock.services.currency import get_principal_devise

    devise_principale = get_principal_devise(entreprise_id)
    dettes = _dettes_qs(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )

    lignes = LigneSortie.objects.filter(sortie__in=sorties).annotate(
        line_total_reference=_LINE_REFERENCE_TOTAL
    )
    agg = lignes.aggregate(
        total=Sum("line_total_reference"),
        nb_lignes=Count("id"),
    )
    dette_reste = _amount(dettes.aggregate(reste=Sum("reste"))["reste"])

    payload = {
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
        "dette_restante": _amount_str(dette_reste),
        "devise_principale_sigle": devise_principale.sigle if devise_principale else None,
        "nombre_lignes_produits": agg["nb_lignes"] or 0,
    }
    if include_produits:
        payload["produits_achetes"] = build_produits_achetes(
            sorties,
            devise_principale=devise_principale,
        )
    else:
        payload["produits_achetes"] = []
    return payload


def build_client_statistics(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """Alias du dashboard simplifié (plus de KPIs secondaires)."""
    return build_client_dashboard(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
        include_produits=True,
    )


def build_client_balance(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    """Solde = dette restante — sans charger les produits (perf / ETag léger)."""
    dashboard = build_client_dashboard(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
        include_produits=False,
    )
    return {
        "client": dashboard["client"],
        "periode": dashboard["periode"],
        "dette_restante": dashboard["dette_restante"],
        "nombre_achats": dashboard["nombre_achats"],
        "total_achete": dashboard["total_achete"],
        "devise_principale_sigle": dashboard["devise_principale_sigle"],
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
            montant_total=Sum(_SORTIE_LINE_REFERENCE_TOTAL),
            nombre_lignes=Count("lignes"),
        )
        .order_by("-date_creation", "-id")
    )
    from stock.services.currency import get_principal_devise

    devise_principale = get_principal_devise(entreprise_id)
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
                "devise_principale_sigle": devise_principale.sigle if devise_principale else None,
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
    from stock.services.currency import get_principal_devise

    return build_produits_achetes(
        sorties,
        devise_principale=get_principal_devise(entreprise_id),
    )
