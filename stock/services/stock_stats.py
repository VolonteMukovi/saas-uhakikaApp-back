"""
Agrégations SQL des stocks par statut (NORMAL / ALERTE / RUPTURE) + lots proches expiration.

Règles statut (identiques à StockSerializer.get_statut) :
- RUPTURE : Qte == 0
- ALERTE (stock faible) : Qte > 0 et Qte <= seuilAlert
- NORMAL : Qte > seuilAlert

Expirations : articles distincts ayant au moins une LigneEntree avec quantite_restante > 0,
date_expiration renseignée, entre aujourd'hui (inclus) et une date fin (inclus).
Deux fenêtres : 30 jours glissants, et 3 mois calendaires.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from django.db.models import Count, F, Q
from django.utils import timezone

from stock.models import LigneEntree, Stock


def _add_months(d: date, months: int) -> date:
    """Ajoute des mois calendaires (sans dépendre de python-dateutil)."""
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


def _count_articles_expiration_dans_fenetre(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    date_fin_inclusive: date,
    today: date | None = None,
) -> tuple[int, date, date]:
    """
    Articles distincts avec au moins un lot non épuisé dont la date d'expiration est
    dans [aujourd'hui, date_fin_inclusive] (lots déjà expirés exclus).
    """
    if today is None:
        today = timezone.now().date()
    le = LigneEntree.objects.filter(
        article__entreprise_id=entreprise_id,
        quantite_restante__gt=0,
        date_expiration__isnull=False,
        date_expiration__gte=today,
        date_expiration__lte=date_fin_inclusive,
    )
    if succursale_id is not None:
        le = le.filter(article__succursale_id=succursale_id)

    n = le.values('article').distinct().count()
    return int(n), today, date_fin_inclusive


def aggregate_stock_stats(
    *,
    entreprise_id: int,
    succursale_id: int | None,
) -> dict[str, Any]:
    """
    Compte les lignes Stock (1 requête agrégée), puis les articles à expiration
    sous 30 jours et sous 3 mois (2 requêtes distinctes).
    """
    qs = Stock.objects.filter(article__entreprise_id=entreprise_id)
    if succursale_id is not None:
        qs = qs.filter(article__succursale_id=succursale_id)

    row = qs.aggregate(
        total=Count('pk'),
        rupture=Count('pk', filter=Q(Qte=0)),
        alerte=Count(
            'pk',
            filter=Q(Qte__gt=0) & Q(Qte__lte=F('seuilAlert')),
        ),
        normal=Count('pk', filter=Q(Qte__gt=F('seuilAlert'))),
    )

    total = int(row['total'] or 0)
    rupture = int(row['rupture'] or 0)
    alerte = int(row['alerte'] or 0)
    normal = int(row['normal'] or 0)

    sum_statuts = normal + alerte + rupture

    today = timezone.now().date()
    fin_30 = today + timedelta(days=30)
    fin_3m = _add_months(today, 3)

    exp30_n, d0_30, d30 = _count_articles_expiration_dans_fenetre(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        date_fin_inclusive=fin_30,
        today=today,
    )
    exp3m_n, d0_3m, d3m = _count_articles_expiration_dans_fenetre(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        date_fin_inclusive=fin_3m,
        today=today,
    )

    return {
        'total': total,
        'normal': normal,
        'alerte': alerte,
        'faible': alerte,
        'rupture': rupture,
        'sum_statuts': sum_statuts,
        'by_code': {
            'NORMAL': normal,
            'ALERTE': alerte,
            'RUPTURE': rupture,
        },
        'expiration_sous_30_jours': exp30_n,
        'expiration_periode_30_jours': {
            'date_debut': d0_30.isoformat(),
            'date_fin': d30.isoformat(),
        },
        'expiration_sous_3_mois': exp3m_n,
        'expiration_periode': {
            'date_debut': d0_3m.isoformat(),
            'date_fin': d3m.isoformat(),
        },
    }
