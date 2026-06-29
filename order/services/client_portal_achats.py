"""
Historique d'achats client (lignes de sortie) — requêtes optimisées pour le portail et le back-office.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any, Optional

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date

from order.branch_scope import branch_q_for_ligne_sortie
from stock.models import Client, ClientEntreprise, LigneSortie


def _q5(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _amount_str(value) -> str:
    return f"{_q5(value):.5f}"


def parse_achats_filters(request) -> dict[str, Any]:
    qp = request.query_params
    date_debut = parse_date(str(qp.get('date_debut') or qp.get('date_min') or '')[:10] or '')
    date_fin = parse_date(str(qp.get('date_fin') or qp.get('date_max') or '')[:10] or '')
    if date_debut and date_fin and date_debut > date_fin:
        raise ValueError('date_debut doit etre inferieure ou egale a date_fin.')

    statut = qp.get('statut')
    if statut and statut not in ('PAYEE', 'EN_CREDIT'):
        statut = None

    article_code = (qp.get('article') or qp.get('article_id') or qp.get('article_code') or '').strip()
    q = (qp.get('q') or qp.get('search') or '').strip()

    return {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'statut': statut,
        'article_code': article_code or None,
        'q': q or None,
    }


def _montant_ligne_expr():
    return ExpressionWrapper(
        F('quantite') * F('prix_unitaire'),
        output_field=DecimalField(max_digits=14, decimal_places=5),
    )


def achats_lignes_qs(
    *,
    client: Client,
    entreprise_id: int,
    branch_q: Q,
    filters: Optional[dict] = None,
):
    """
    Lignes d'achat (LigneSortie) du client — une requête, pas de N+1.
    """
    filters = filters or {}
    qs = (
        LigneSortie.objects.filter(
            sortie__client=client,
            sortie__entreprise_id=entreprise_id,
        )
        .filter(branch_q)
        .select_related('article', 'devise', 'sortie')
        .annotate(montant_ligne=_montant_ligne_expr())
        .order_by('-date_sortie', '-id')
    )

    if filters.get('date_debut'):
        qs = qs.filter(date_sortie__date__gte=filters['date_debut'])
    if filters.get('date_fin'):
        qs = qs.filter(date_sortie__date__lte=filters['date_fin'])
    if filters.get('statut'):
        qs = qs.filter(sortie__statut=filters['statut'])
    if filters.get('article_code'):
        qs = qs.filter(article_id=filters['article_code'])
    if filters.get('q'):
        qs = qs.filter(
            Q(article__nom_scientifique__icontains=filters['q'])
            | Q(article__nom_commercial__icontains=filters['q'])
            | Q(article_id__icontains=filters['q'])
        )

    return qs


def achats_par_article(
    *,
    client: Client,
    entreprise_id: int,
    branch_q: Q,
    filters: Optional[dict] = None,
    limit: int = 100,
):
    """
    Synthèse par article (agrégation SQL — performant pour « mes produits achetés »).
    """
    filters = filters or {}
    base = achats_lignes_qs(
        client=client,
        entreprise_id=entreprise_id,
        branch_q=branch_q,
        filters=filters,
    )
    rows = (
        base.values(
            'article_id',
            'article__nom_scientifique',
            'article__nom_commercial',
        )
        .annotate(
            quantite_totale=Coalesce(Sum('quantite'), Value(0), output_field=DecimalField(max_digits=14, decimal_places=5)),
            montant_total=Coalesce(Sum(_montant_ligne_expr()), Value(0), output_field=DecimalField(max_digits=14, decimal_places=5)),
            nombre_achats=Count('id'),
            dernier_achat=Max('date_sortie'),
        )
        .order_by('-dernier_achat')[:limit]
    )

    return [
        {
            'article_id': row['article_id'],
            'nom_scientifique': row['article__nom_scientifique'],
            'nom_commercial': row['article__nom_commercial'],
            'quantite_totale': _amount_str(row['quantite_totale']),
            'montant_total': _amount_str(row['montant_total']),
            'nombre_achats': row['nombre_achats'],
            'dernier_achat': row['dernier_achat'].isoformat() if row['dernier_achat'] else None,
        }
        for row in rows
    ]


def serialize_achat_ligne(ligne: LigneSortie) -> dict:
    art = ligne.article
    dev = ligne.devise
    sortie = ligne.sortie
    montant = getattr(ligne, 'montant_ligne', None)
    if montant is None:
        montant = _q5(ligne.quantite * ligne.prix_unitaire)
    return {
        'id': ligne.pk,
        'sortie_id': ligne.sortie_id,
        'sortie_statut': sortie.statut if sortie else None,
        'sortie_date': sortie.date_creation.isoformat() if sortie and sortie.date_creation else None,
        'date_achat': ligne.date_sortie.isoformat() if ligne.date_sortie else None,
        'article': {
            'article_id': art.article_id if art else ligne.article_id,
            'nom_scientifique': art.nom_scientifique if art else None,
            'nom_commercial': art.nom_commercial if art else None,
        },
        'quantite': _amount_str(ligne.quantite),
        'prix_unitaire': _amount_str(ligne.prix_unitaire),
        'montant_ligne': _amount_str(montant),
        'devise': {
            'id': dev.pk,
            'sigle': dev.sigle,
            'symbole': dev.symbole,
        } if dev else None,
    }


def achats_recents_payload(
    *,
    client: Client,
    membership: ClientEntreprise,
    limit: int = 8,
) -> list[dict]:
    """Aperçu léger pour le dashboard (évite de charger toutes les sorties + lignes)."""
    bq = branch_q_for_ligne_sortie(membership)
    qs = achats_lignes_qs(
        client=client,
        entreprise_id=membership.entreprise_id,
        branch_q=bq,
    )[:limit]
    return [serialize_achat_ligne(l) for l in qs]
