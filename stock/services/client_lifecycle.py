from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from caisse.models import MouvementCaisse
from stock.models import Client, DetteClient, LigneSortie, Sortie
from stock.services.credit_sale_debt import resolve_sortie_primary_devise
from stock.services.dette_statut import compute_statut_dette, solde_effectif


ZERO = Decimal("0.00000")
_MONEY_FIELD = DecimalField(max_digits=14, decimal_places=5)


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


def _paiements_par_devise_resolue(paiements, dettes) -> dict[int | None, Decimal]:
    """Somme des paiements par devise (fallback : devise de la dette si paiement sans devise)."""
    dette_devise = {d.pk: d.devise_id for d in dettes}
    totals: dict[int | None, Decimal] = {}
    for paiement in paiements:
        devise_id = paiement.devise_id or dette_devise.get(paiement.object_id)
        applied = paiement.montant_applique if paiement.montant_applique is not None else paiement.montant
        totals[devise_id] = totals.get(devise_id, ZERO) + _amount(applied)
    return totals


def _sum_paiements(paiements_qs) -> Decimal:
    """Préfère montant_applique (devise dette) quand présent."""
    agg = paiements_qs.aggregate(
        total=Sum(
            Coalesce(
                F('montant_applique'),
                F('montant'),
                output_field=_MONEY_FIELD,
            )
        )
    )
    return _amount(agg['total'])


def _compute_du_actuel(all_dettes_qs) -> tuple[Decimal, dict[int | None, Decimal], dict[str, int]]:
    """
    Dû réel actuel = Σ soldes effectifs des créances encore ouvertes
    (indépendant du filtre de période).
    """
    qs = all_dettes_qs.with_paiements_aggregate().select_related('devise')
    du = ZERO
    by_devise: dict[int | None, Decimal] = {}
    counts = {'en_cours': 0, 'retard': 0, 'payees': 0, 'ouvertes': 0}
    for d in qs.iterator(chunk_size=200):
        paye_agg = getattr(d, 'montant_paye_agg', None)
        solde_brut = (
            _amount(d.montant_total) - _amount(paye_agg)
            if paye_agg is not None
            else None
        )
        solde = solde_effectif(d, solde=solde_brut)
        statut = compute_statut_dette(d, solde=solde_brut)
        if statut == 'PAYEE' or solde <= 0:
            counts['payees'] += 1
            continue
        if statut == 'RETARD':
            counts['retard'] += 1
        else:
            counts['en_cours'] += 1
        counts['ouvertes'] += 1
        du += solde
        did = d.devise_id
        by_devise[did] = by_devise.get(did, ZERO) + solde
    return du, by_devise, counts


def _client_base_querysets(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    date_debut = period["_date_debut"]
    date_fin = period["_date_fin"]

    sorties = Sortie.objects.filter(client=client, entreprise_id=entreprise_id)
    dettes = DetteClient.objects.filter(client=client, entreprise_id=entreprise_id)
    if succursale_id is not None:
        sorties = sorties.filter(succursale_id=succursale_id)
        dettes = dettes.filter(succursale_id=succursale_id)

    sorties = _period_lookup(sorties, "date_creation__date", date_debut, date_fin)
    dettes = _period_lookup(dettes, "date_creation__date", date_debut, date_fin)

    # Les ventes EN_CREDIT dont la dette a été supprimée ne doivent plus
    # apparaître dans les stats / mouvements (évite CA & total_credit fantômes).
    sorties = sorties.filter(
        Q(statut="PAYEE") | Q(statut="EN_CREDIT", dette__isnull=False)
    )

    line_total_expr = ExpressionWrapper(
        F("quantite") * F("prix_unitaire"),
        output_field=DecimalField(max_digits=14, decimal_places=5),
    )
    lignes = LigneSortie.objects.filter(sortie__in=sorties).annotate(line_total=line_total_expr)

    ct_dette = ContentType.objects.get_for_model(DetteClient)
    all_dettes = DetteClient.objects.filter(client=client, entreprise_id=entreprise_id)
    if succursale_id is not None:
        all_dettes = all_dettes.filter(succursale_id=succursale_id)

    def _paiements_base(dettes_scope):
        qs_pay = (
            MouvementCaisse.objects.filter(
                entreprise_id=entreprise_id,
                type="ENTREE",
                content_type=ct_dette,
                object_id__in=dettes_scope.values("pk"),
            )
            .select_related("devise", "utilisateur", "type_caisse", "session_caisse")
            .order_by("-date", "-id")
        )
        if succursale_id is not None:
            qs_pay = qs_pay.filter(succursale_id=succursale_id)
        return qs_pay

    # Encaissements datés dans la fenêtre (historique / mouvements)
    paiements = _period_lookup(_paiements_base(all_dettes), "date__date", date_debut, date_fin)
    # Payé sur les créances nées dans la période (= aligné sur total_credit / total_dettes)
    paiements_sur_dettes_periode = _paiements_base(dettes)

    return {
        "sorties": sorties,
        "dettes": dettes,
        "all_dettes": all_dettes,
        "lignes": lignes,
        "paiements": paiements,
        "paiements_sur_dettes_periode": paiements_sur_dettes_periode,
    }


def build_client_dashboard(*, client: Client, entreprise_id: int, succursale_id: int | None, period: dict):
    qs = _client_base_querysets(
        client=client,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        period=period,
    )
    sorties = qs["sorties"]
    dettes = qs["dettes"]
    all_dettes = qs["all_dettes"]
    lignes = qs["lignes"]
    paiements = qs["paiements"]
    paiements_sur_dettes_periode = qs["paiements_sur_dettes_periode"]

    ventes_agg = lignes.aggregate(
        total_comptant=Sum("line_total", filter=Q(sortie__statut="PAYEE")),
    )

    # Activité de la période :
    # - total_credit / total_dettes = créances nées dans la fenêtre
    # - total_paye = montants payés sur ces mêmes créances (pas les encaissements
    #   d'anciennes dettes hors période, qui faussaient le KPI « Total payé »)
    total_dettes = _amount(dettes.aggregate(total=Sum("montant_total"))["total"])
    total_credit = total_dettes
    total_comptant = _amount(ventes_agg["total_comptant"])
    total_montant = _amount(total_comptant + total_credit)
    total_paye = _sum_paiements(paiements_sur_dettes_periode)
    ecart_periode = _amount(total_credit - total_paye)

    # Dû réel actuel (toutes créances ouvertes, hors filtre période)
    du_actuel, du_par_devise, counts_ouverts = _compute_du_actuel(all_dettes)
    # Alias principal pour l'UI : « Solde restant » = ce que le client doit encore
    solde_restant = du_actuel

    last_sortie = sorties.order_by("-date_creation", "-id").select_related("devise").first()
    last_paiement = paiements.first()

    derniere_operation = {"date": None, "type": None, "montant": "0.00000", "devise": None}
    candidates = []
    if last_sortie is not None:
        sortie_total = _amount(
            last_sortie.lignes.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("quantite") * F("prix_unitaire"),
                        output_field=DecimalField(max_digits=14, decimal_places=5),
                    )
                )
            )["total"]
        )
        candidates.append(
            {
                "date": last_sortie.date_creation,
                "type": "VENTE_COMPTANT" if last_sortie.statut == "PAYEE" else "VENTE_CREDIT",
                "montant": _amount_str(sortie_total),
                "devise": _sortie_devise_sigle(last_sortie) or (last_sortie.devise.sigle if last_sortie.devise else None),
            }
        )
    if last_paiement is not None:
        applied = (
            last_paiement.montant_applique
            if last_paiement.montant_applique is not None
            else last_paiement.montant
        )
        candidates.append(
            {
                "date": last_paiement.date,
                "type": "PAIEMENT_DETTE",
                "montant": _amount_str(applied),
                "devise": last_paiement.devise.sigle if last_paiement.devise else None,
            }
        )
    if candidates:
        top = max(candidates, key=lambda item: item["date"])
        derniere_operation = {
            "date": top["date"].isoformat() if top["date"] else None,
            "type": top["type"],
            "montant": top["montant"],
            "devise": top["devise"],
        }

    totaux_par_devise = []
    dette_by_devise = dettes.values("devise__id", "devise__sigle").annotate(
        total_credit=Sum("montant_total"),
        nombre_dettes=Count("id"),
    )
    paiement_map = _paiements_par_devise_resolue(
        list(paiements_sur_dettes_periode),
        list(dettes),
    )
    seen_devise_ids: set[int | None] = set()
    for row in dette_by_devise:
        devise_id = row["devise__id"]
        seen_devise_ids.add(devise_id)
        total_credit_devise = _amount(row["total_credit"])
        total_paye_devise = paiement_map.get(devise_id, ZERO)
        du_devise = du_par_devise.get(devise_id, ZERO)
        totaux_par_devise.append(
            {
                "devise": row["devise__sigle"],
                "devise_id": devise_id,
                "total_credit": _amount_str(total_credit_devise),
                "total_paye": _amount_str(total_paye_devise),
                "ecart_periode": _amount_str(total_credit_devise - total_paye_devise),
                "du_actuel": _amount_str(du_devise),
                "solde": _amount_str(du_devise),
                "nombre_dettes": row["nombre_dettes"],
            }
        )
    for devise_id, du_val in du_par_devise.items():
        if devise_id in seen_devise_ids or du_val <= 0:
            continue
        sigle = None
        if devise_id:
            from stock.models import Devise
            d = Devise.objects.filter(pk=devise_id).only('sigle').first()
            sigle = d.sigle if d else None
        totaux_par_devise.append(
            {
                "devise": sigle,
                "devise_id": devise_id,
                "total_credit": _amount_str(ZERO),
                "total_paye": _amount_str(paiement_map.get(devise_id, ZERO)),
                "ecart_periode": _amount_str(ZERO - paiement_map.get(devise_id, ZERO)),
                "du_actuel": _amount_str(du_val),
                "solde": _amount_str(du_val),
                "nombre_dettes": 0,
            }
        )
    orphan_paye = paiement_map.get(None, ZERO)
    if orphan_paye > ZERO and None not in seen_devise_ids:
        totaux_par_devise.append(
            {
                "devise": None,
                "devise_id": None,
                "total_credit": _amount_str(ZERO),
                "total_paye": _amount_str(orphan_paye),
                "ecart_periode": _amount_str(-orphan_paye),
                "du_actuel": _amount_str(du_par_devise.get(None, ZERO)),
                "solde": _amount_str(du_par_devise.get(None, ZERO)),
                "nombre_dettes": 0,
            }
        )

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
            "nombre_operations": sorties.count() + paiements_sur_dettes_periode.count(),
            "chiffre_affaires_total": _amount_str(total_montant),
            "total_comptant": _amount_str(total_comptant),
            "total_credit": _amount_str(total_credit),
            "total_dettes": _amount_str(total_dettes),
            "total_paye": _amount_str(total_paye),
            "du_actuel": _amount_str(du_actuel),
            "solde_restant": _amount_str(solde_restant),
            "ecart_periode": _amount_str(ecart_periode),
            "nombre_ventes": sorties.count(),
            "nombre_dettes": dettes.count(),
            "nombre_paiements": paiements_sur_dettes_periode.count(),
            "nombre_dettes_ouvertes": counts_ouverts["ouvertes"],
        },
        "repartition": {
            "comptant": _amount_str(total_comptant),
            "credit": _amount_str(total_credit),
            "dettes_en_cours": counts_ouverts["en_cours"],
            "dettes_payees": counts_ouverts["payees"],
            "dettes_en_retard": counts_ouverts["retard"],
            "dettes_periode_en_cours": dettes.filter(statut="EN_COURS").count(),
            "dettes_periode_payees": dettes.filter(statut="PAYEE").count(),
            "dettes_periode_en_retard": dettes.filter(statut="RETARD").count(),
        },
        "derniere_operation": derniere_operation,
        "totaux_par_devise": totaux_par_devise,
        "instructions_frontend": {
            "solde_restant": (
                "Afficher comme « Solde restant » / « Dû actuel » : ce que le client doit encore "
                "(créances ouvertes). Ne dépend pas du filtre de période."
            ),
            "du_actuel": "Alias explicite de solde_restant (même valeur).",
            "ecart_periode": (
                "« Écart période » = total_credit − total_paye sur les créances nées "
                "dans la fenêtre (peut être 0 si ces dettes sont soldées). "
                "Ne pas l'afficher comme le dû global du client (voir du_actuel)."
            ),
            "total_credit": "Dettes / crédits nés dans la période.",
            "total_paye": (
                "Montant payé sur les dettes nées dans la période "
                "(même périmètre que total_credit / total_dettes). "
                "N’inclut pas les paiements d’anciennes créances hors fenêtre."
            ),
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
        total = sortie.lignes.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantite") * F("prix_unitaire"),
                    output_field=DecimalField(max_digits=14, decimal_places=5),
                )
            )
        )["total"]
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
    paiements = qs["paiements"].select_related("devise", "utilisateur", "type_caisse", "session_caisse").order_by("date", "id")
    sortie_mouvements = _sortie_mouvement_map(sorties.values_list("pk", flat=True))

    movements = []
    # Solde courant des écritures de la période (activité), pas le dû global
    running_balance = ZERO

    for sortie in sorties:
        total = _amount(
            sortie.lignes.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F("quantite") * F("prix_unitaire"),
                        output_field=DecimalField(max_digits=14, decimal_places=5),
                    )
                )
            )["total"]
        )
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

    for paiement in paiements:
        applied = paiement.montant_applique if paiement.montant_applique is not None else paiement.montant
        running_balance -= _amount(applied)
        movements.append(
            {
                "date": paiement.date,
                "type": "PAIEMENT_DETTE",
                "reference": paiement.reference_piece or f"PAIEMENT-{paiement.pk}",
                "libelle": paiement.motif_affiche() or "Paiement de dette",
                "debit": _amount_str(ZERO),
                "credit": _amount_str(applied),
                "montant": _amount_str(applied),
                "solde_apres_operation": _amount_str(running_balance),
                "devise": paiement.devise.sigle if paiement.devise else None,
                "statut": "VALIDE",
                "utilisateur": (
                    paiement.utilisateur.get_full_name() or paiement.utilisateur.username
                    if paiement.utilisateur
                    else None
                ),
                "session_caisse": paiement.session_caisse_id,
                "type_caisse": paiement.type_caisse.libelle_affiche if paiement.type_caisse else None,
                "description": paiement.motif or "",
                "impact_solde": "diminue_solde",
            }
        )

    movements.sort(key=lambda item: (item["date"], item["reference"]))
    for item in movements:
        item["date"] = item["date"].isoformat() if item["date"] else None
    movements.reverse()
    return movements
