"""
Filtres query string pour le module transit (lots, frais, items, fournisseurs).
Sans dépendance django-filter : requêtes explicites et index-friendly.
"""
from datetime import datetime

from django.db.models import Q


def _parse_date(value: str):
    if not value or not str(value).strip():
        return None
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def apply_fournisseur_filters(qs, request):
    """Filtres liste fournisseurs : search, is_active, dates de création."""
    p = request.query_params

    if p.get("is_active") is not None:
        v = str(p.get("is_active")).strip().lower()
        if v in ("true", "1", "yes", "oui"):
            qs = qs.filter(is_active=True)
        elif v in ("false", "0", "no", "non"):
            qs = qs.filter(is_active=False)

    d0 = p.get("created_at_min") or p.get("date_creation_min")
    d1 = p.get("created_at_max") or p.get("date_creation_max")
    if d0:
        try:
            qs = qs.filter(created_at__date__gte=_parse_date(d0))
        except ValueError:
            pass
    if d1:
        try:
            qs = qs.filter(created_at__date__lte=_parse_date(d1))
        except ValueError:
            pass

    q = (p.get("search") or p.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(nom__icontains=q)
            | Q(code__icontains=q)
            | Q(telephone__icontains=q)
            | Q(email__icontains=q)
            | Q(nif__icontains=q)
        )
    return qs


def apply_lot_filters(qs, request):
    """Filtres liste lots : fournisseur, statut, dates, référence, recherche texte."""
    p = request.query_params

    if p.get("fournisseur_id"):
        try:
            qs = qs.filter(fournisseur_id=int(p.get("fournisseur_id")))
        except (TypeError, ValueError):
            pass

    if p.get("statut"):
        qs = qs.filter(statut=p.get("statut"))

    for key, field in (
        ("date_expedition_min", "date_expedition__gte"),
        ("date_expedition_max", "date_expedition__lte"),
        ("date_expedition_from", "date_expedition__gte"),
        ("date_expedition_to", "date_expedition__lte"),
    ):
        if p.get(key):
            try:
                qs = qs.filter(**{field: _parse_date(p.get(key))})
            except ValueError:
                pass

    for key, field in (
        ("date_arrivee_prevue_min", "date_arrivee_prevue__gte"),
        ("date_arrivee_prevue_max", "date_arrivee_prevue__lte"),
        ("date_arrivee_prevue_from", "date_arrivee_prevue__gte"),
        ("date_arrivee_prevue_to", "date_arrivee_prevue__lte"),
    ):
        if p.get(key):
            try:
                qs = qs.filter(**{field: _parse_date(p.get(key))})
            except ValueError:
                pass

    if p.get("reference"):
        qs = qs.filter(reference__icontains=p.get("reference").strip())

    q = (p.get("search") or "").strip()
    if q:
        qs = qs.filter(
            Q(reference__icontains=q)
            | Q(fournisseur__nom__icontains=q)
            | Q(fournisseur__code__icontains=q)
        )

    return qs


def apply_frais_lot_filters(qs, request):
    p = request.query_params
    if p.get("lot_id"):
        try:
            qs = qs.filter(lot_id=int(p.get("lot_id")))
        except (TypeError, ValueError):
            pass
    if p.get("type_frais"):
        qs = qs.filter(type_frais=p.get("type_frais"))
    if p.get("devise_id"):
        try:
            qs = qs.filter(devise_id=int(p.get("devise_id")))
        except (TypeError, ValueError):
            pass
    for key, field in (
        ("created_at_min", "created_at__date__gte"),
        ("created_at_max", "created_at__date__lte"),
    ):
        if p.get(key):
            try:
                qs = qs.filter(**{field: _parse_date(p.get(key))})
            except ValueError:
                pass
    return qs


def apply_lot_item_filters(qs, request):
    p = request.query_params
    if p.get("lot_id"):
        try:
            qs = qs.filter(lot_id=int(p.get("lot_id")))
        except (TypeError, ValueError):
            pass
    if p.get("article_id"):
        qs = qs.filter(article_id=p.get("article_id").strip())
    return qs


def apply_ordering(qs, request, allowed: dict, default: str):
    """
    Paramètre `ordering` : nom de champ ; préfixe `-` pour tri décroissant.
    `allowed` : { nom_param: nom_champ Django pour order_by }.
    """
    raw = (request.query_params.get("ordering") or default or "").strip()
    if not raw:
        return qs.order_by(default) if default else qs
    desc = raw.startswith("-")
    key = raw[1:] if desc else raw
    if key not in allowed:
        return qs.order_by(default) if default else qs
    field = allowed[key]
    if desc:
        field = f"-{field}"
    return qs.order_by(field)
