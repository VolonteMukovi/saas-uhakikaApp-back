"""Filtres query string pour les commandes (admin / listes)."""
from datetime import datetime

from django.db.models import Q


def _parse_dt_date(value: str):
    if not value or not str(value).strip():
        return None
    return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()


def apply_commande_filters(qs, request):
    p = request.query_params

    if p.get("statut"):
        qs = qs.filter(statut=p.get("statut").strip())

    if p.get("client_id"):
        qs = qs.filter(client_id=p.get("client_id").strip())

    for key, lookup in (
        ("created_at_min", "created_at__date__gte"),
        ("created_at_max", "created_at__date__lte"),
        ("date_debut", "created_at__date__gte"),
        ("date_fin", "created_at__date__lte"),
    ):
        if p.get(key):
            try:
                qs = qs.filter(**{lookup: _parse_dt_date(p.get(key))})
            except ValueError:
                pass

    if p.get("reference"):
        qs = qs.filter(reference__icontains=p.get("reference").strip())

    q = (p.get("search") or "").strip()
    if q:
        qs = qs.filter(
            Q(reference__icontains=q)
            | Q(note_client__icontains=q)
            | Q(client__nom__icontains=q)
            | Q(items__article__nom_scientifique__icontains=q)
            | Q(items__article__nom_commercial__icontains=q)
            | Q(items__nom_article__icontains=q)
        ).distinct()

    return qs


def apply_commande_ordering(qs, request, default="-created_at"):
    raw = (request.query_params.get("ordering") or default or "").strip()
    allowed = {
        "created_at": "created_at",
        "updated_at": "updated_at",
        "statut": "statut",
        "reference": "reference",
        "id": "id",
    }
    if not raw:
        return qs.order_by(default)
    desc = raw.startswith("-")
    key = raw[1:] if desc else raw
    if key not in allowed:
        return qs.order_by(default)
    field = allowed[key]
    if desc:
        field = f"-{field}"
    return qs.order_by(field)
