from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone

from caisse.models import MouvementCaisse
from stock.models import Client, LigneSortie, Sortie
from stock.services.sortie_devise import resolve_sortie_primary_devise

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


def _sortie_devise_sigle(sortie: Sortie) -> str | None:
    devise = resolve_sortie_primary_devise(sortie)
    return devise.sigle if devise else None


def _sortie_mouvement_map(sortie_ids) -> dict[int, MouvementCaisse]:
    if not sortie_ids:
        return {}
    rows = (
        MouvementCaisse.objects.filter(sortie_id__in=sortie_ids)
        .select_related('utilisateur', 'type_caisse', 'session_caisse', 'devise')
        .order_by('sortie_id', 'id')
    )
    out = {}
    for mc in rows:
        if mc.sortie_id and mc.sortie_id not in out:
            out[mc.sortie_id] = mc
    return out


def _credit_total_for_sorties(sorties_qs) -> Decimal:
    lignes = LigneSortie.objects.filter(sortie__in=sorties_qs.filter(statut="EN_CREDIT"))
    agg = lignes.aggregate(total=Sum(_LINE_TOTAL))
    return _amount(agg["total"])


def _totaux_par_devise_from_sorties(sorties_qs) -> list[dict]:
    credit_sorties = sorties_qs.filter(statut="EN_CREDIT")
    rows = (
        LigneSortie.objects.filter(sortie__in=credit_sorties)
        .values("devise__id", "devise__sigle")
        .annotate(total_credit=Sum(_LINE_TOTAL), nombre_ventes_credit=Count("sortie_id", distinct=True))
    )
    result = []
    for row in rows:
        total_credit_devise = _amount(row["total_credit"])
        result.append(
            {
                "devise": row["devise__sigle"],
                "devise_id": row["devise__id"],
                "total_credit": _amount_str(total_credit_devise),
                "total_paye": _amount_str(ZERO),
                "ecart_periode": _amount_str(total_credit_devise),
                "du_actuel": _amount_str(ZERO),
                "solde": _amount_str(ZERO),
                "nombre_dettes": row["nombre_ventes_credit"],
            }
        )
    return result


def _client_base_querysets(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    date_debut = period["_date_debut"]
    date_fin = period["_date_fin"]

    sorties = Sortie.objects.filter(client=client, entreprise_id=entreprise_id)
    if succursale_id is not None:
        sorties = sorties.filter(succursale_id=succursale_id)

    sorties = _period_lookup(sorties, "date_creation__date", date_debut, date_fin)
    lignes = LigneSortie.objects.filter(sortie__in=sorties).annotate(line_total=_LINE_TOTAL)

    return {
        "sorties": sorties,
        "lignes": lignes,
    }


def build_client_dashboard(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    qs = _client_base_querysets(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    sorties = qs["sorties"]
    lignes = qs["lignes"]

    ventes_agg = lignes.aggregate(
        total_comptant=Sum("line_total", filter=Q(sortie__statut="PAYEE")),
    )

    total_credit = _credit_total_for_sorties(sorties)
    total_dettes = total_credit
    total_comptant = _amount(ventes_agg["total_comptant"])
    total_montant = _amount(total_comptant + total_credit)
    total_paye = ZERO
    ecart_periode = total_credit
    du_actuel = ZERO
    solde_restant = ZERO

    last_sortie = sorties.order_by("-date_creation", "-id").select_related("devise").first()

    derniere_operation = {"date": None, "type": None, "montant": "0.00000", "devise": None}
    if last_sortie is not None:
        sortie_total = _amount(
            last_sortie.lignes.aggregate(total=Sum(_LINE_TOTAL))["total"]
        )
        derniere_operation = {
            "date": last_sortie.date_creation.isoformat() if last_sortie.date_creation else None,
            "type": "VENTE_COMPTANT" if last_sortie.statut == "PAYEE" else "VENTE_CREDIT",
            "montant": _amount_str(sortie_total),
            "devise": _sortie_devise_sigle(last_sortie) or (last_sortie.devise.sigle if last_sortie.devise else None),
        }

    nombre_ventes_credit = sorties.filter(statut="EN_CREDIT").count()

    return {
        "client": {
            "id": client.pk,
            "nom": client.nom,
            "telephone": client.telephone,
            "email": client.email,
            "adresse": client.adresse,
        },
        "periode": {
            "date_debut": period["date_debut"],
            "date_fin": period["date_fin"],
            "mode": period["mode"],
        },
        "resume": {
            "nombre_operations": sorties.count(),
            "chiffre_affaires_total": _amount_str(total_montant),
            "total_comptant": _amount_str(total_comptant),
            "total_credit": _amount_str(total_credit),
            "total_dettes": _amount_str(total_dettes),
            "total_paye": _amount_str(total_paye),
            "du_actuel": _amount_str(du_actuel),
            "solde_restant": _amount_str(solde_restant),
            "ecart_periode": _amount_str(ecart_periode),
            "nombre_ventes": sorties.count(),
            "nombre_dettes": nombre_ventes_credit,
            "nombre_paiements": 0,
            "nombre_dettes_ouvertes": 0,
        },
        "repartition": {
            "comptant": _amount_str(total_comptant),
            "credit": _amount_str(total_credit),
            "dettes_en_cours": 0,
            "dettes_payees": 0,
            "dettes_en_retard": 0,
            "dettes_periode_en_cours": nombre_ventes_credit,
            "dettes_periode_payees": 0,
            "dettes_periode_en_retard": 0,
        },
        "derniere_operation": derniere_operation,
        "totaux_par_devise": _totaux_par_devise_from_sorties(sorties),
        "instructions_frontend": {
            "solde_restant": "Le suivi des créances client (dettes) n'est plus disponible sur cette API.",
            "du_actuel": "Toujours 0 — ancien module dettes retiré.",
            "ecart_periode": "Montant des ventes à crédit sur la période (sans paiements dettes).",
            "total_credit": "Ventes EN_CREDIT sur la période.",
            "total_paye": "Toujours 0 — paiements dettes retirés.",
        },
    }


def build_client_statistics(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    dashboard = build_client_dashboard(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    qs = _client_base_querysets(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    nombre_ventes = dashboard["resume"]["nombre_ventes"]
    chiffre_affaires_total = _amount(dashboard["resume"]["chiffre_affaires_total"])
    montant_moyen = ZERO if nombre_ventes == 0 else (chiffre_affaires_total / Decimal(nombre_ventes))
    dashboard["statistiques"] = {
        "montant_moyen_par_vente": _amount_str(montant_moyen),
        "nombre_ventes_comptant": qs["sorties"].filter(statut="PAYEE").count(),
        "nombre_ventes_credit": qs["sorties"].filter(statut="EN_CREDIT").count(),
    }
    return dashboard


def build_client_balance(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    dashboard = build_client_dashboard(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    return {
        "client": dashboard["client"],
        "periode": dashboard["periode"],
        "solde": {
            "total_du": dashboard["resume"]["total_dettes"],
            "total_paye": dashboard["resume"]["total_paye"],
            "du_actuel": dashboard["resume"]["du_actuel"],
            "solde_restant": dashboard["resume"]["solde_restant"],
            "ecart_periode": dashboard["resume"]["ecart_periode"],
        },
        "totaux_par_devise": dashboard["totaux_par_devise"],
        "instructions_frontend": dashboard.get("instructions_frontend"),
    }


def build_client_sales(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    qs = _client_base_querysets(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    sorties = qs["sorties"].select_related("devise").order_by("-date_creation", "-id")
    results = []
    for sortie in sorties:
        total = sortie.lignes.aggregate(total=Sum(_LINE_TOTAL))["total"]
        results.append(
            {
                "id": sortie.pk,
                "date": sortie.date_creation.isoformat() if sortie.date_creation else None,
                "reference": f"SORTIE-{sortie.pk}",
                "type": "VENTE_COMPTANT" if sortie.statut == "PAYEE" else "VENTE_CREDIT",
                "statut": sortie.statut,
                "montant_total": _amount_str(total),
                "devise": _sortie_devise_sigle(sortie) or (sortie.devise.sigle if sortie.devise else None),
                "nombre_lignes": sortie.lignes.count(),
                "motif": sortie.motif or "",
            }
        )
    return results


def build_client_movements(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    qs = _client_base_querysets(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    sorties = qs["sorties"].select_related("devise").prefetch_related("lignes__devise").order_by("date_creation", "id")
    sortie_mouvements = _sortie_mouvement_map(sorties.values_list("pk", flat=True))

    movements = []
    running_balance = ZERO

    for sortie in sorties:
        total = _amount(sortie.lignes.aggregate(total=Sum(_LINE_TOTAL))["total"])
        mc_sortie = sortie_mouvements.get(sortie.pk)
        if sortie.statut == "EN_CREDIT":
            debit = total
            credit = ZERO
            running_balance += total
            type_operation = "VENTE_CREDIT"
            impact = "augmente_solde"
        else:
            debit = ZERO
            credit = ZERO
            type_operation = "VENTE_COMPTANT"
            impact = "sans_impact_solde"
        movements.append(
            {
                "date": sortie.date_creation,
                "type": type_operation,
                "reference": f"SORTIE-{sortie.pk}",
                "libelle": "Vente a credit" if sortie.statut == "EN_CREDIT" else "Vente au comptant",
                "debit": _amount_str(debit),
                "credit": _amount_str(credit),
                "montant": _amount_str(total),
                "solde_apres_operation": _amount_str(running_balance),
                "devise": _sortie_devise_sigle(sortie),
                "statut": sortie.statut,
                "utilisateur": (
                    mc_sortie.utilisateur.get_full_name() or mc_sortie.utilisateur.username
                    if mc_sortie and mc_sortie.utilisateur
                    else None
                ),
                "session_caisse": mc_sortie.session_caisse_id if mc_sortie else None,
                "type_caisse": mc_sortie.type_caisse.libelle_affiche if mc_sortie and mc_sortie.type_caisse else None,
                "description": sortie.motif or "",
                "impact_solde": impact,
            }
        )

    movements.sort(key=lambda item: (item["date"], item["reference"]))
    for item in movements:
        item["date"] = item["date"].isoformat() if item["date"] else None
    movements.reverse()
    return movements
