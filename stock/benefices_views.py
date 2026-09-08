"""
API performance commerciale : gains, pertes, CA par produit.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from stock.permissions import IsAdminOrUser as StockIsAdminOrUser
from stock.services import benefices_performance as svc
from stock.services.tenant_context import get_tenant_ids


class BeneficePerformanceViewSet(viewsets.ViewSet):
    """
    Lecture seule — analyse des gains / pertes / chiffre d'affaires.

    - GET /api/benefices/resume/
    - GET /api/benefices/articles/?filtre=gains|pertes|tous
    - GET /api/benefices/articles/{article_id}/
    """

    permission_classes = [StockIsAdminOrUser]

    def _contexte(self, request):
        tenant_id, branch_id = get_tenant_ids(request)
        if not tenant_id:
            return None, None, Response(
                {'detail': 'Contexte entreprise manquant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        year, month, _, _ = svc._parse_periode(request.query_params)
        succursale = request.query_params.get('succursale') or request.query_params.get('succursale_id')
        if succursale not in (None, ''):
            try:
                branch_id = int(succursale)
            except (TypeError, ValueError):
                return None, None, Response(
                    {'detail': 'succursale_id invalide.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return (tenant_id, branch_id, year, month), None, None

    @action(detail=False, methods=['get'], url_path='resume')
    def resume(self, request):
        ctx, _, err = self._contexte(request)
        if err:
            return err
        tenant_id, branch_id, year, month = ctx
        data = svc.build_resume(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            year=year,
            month=month,
        )
        return Response(data)

    @action(detail=False, methods=['get'], url_path='articles')
    def articles(self, request):
        ctx, _, err = self._contexte(request)
        if err:
            return err
        tenant_id, branch_id, year, month = ctx
        filtre = (request.query_params.get('filtre') or 'tous').strip().lower()
        if filtre not in ('tous', 'gains', 'pertes'):
            return Response(
                {'detail': 'filtre invalide. Valeurs : tous | gains | pertes'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        search = request.query_params.get('search') or request.query_params.get('q')
        rows = svc.aggregate_par_article(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            year=year,
            month=month,
            filtre=filtre,
            search=search,
        )

        # Pagination manuelle simple
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', 25))
        except (TypeError, ValueError):
            page_size = 25
        page_size = max(1, min(page_size, 200))
        total = len(rows)
        start = (page - 1) * page_size
        slice_rows = rows[start:start + page_size]

        return Response({
            'rapport': 'benefices_articles',
            'periode': {'annee': year, 'mois': month, 'libelle': f'{year}-{month:02d}'},
            'filtre': filtre,
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': slice_rows,
            'instructions_frontend': {
                'onglets_suggeres': ['tous', 'gains', 'pertes'],
                'colonnes': [
                    'designation', 'chiffre_affaires', 'cout_achat',
                    'benefice_net', 'total_gain', 'total_perte', 'statut',
                ],
                'detail_url_template': '/api/benefices/articles/{article_id}/',
            },
        })

    @action(
        detail=False,
        methods=['get'],
        url_path=r'articles/(?P<article_id>[^/.]+)',
    )
    def article_detail(self, request, article_id=None):
        ctx, _, err = self._contexte(request)
        if err:
            return err
        tenant_id, branch_id, year, month = ctx
        data = svc.detail_article(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            article_id=article_id,
            year=year,
            month=month,
        )
        if data is None:
            return Response(
                {'detail': 'Article introuvable pour cette entreprise.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)
