"""
Historique d'achats articles — portail client (performant, paginé).
"""
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.pagination import StandardResultsSetPagination
from stock.models import LigneSortie

from .authentication import ClientJWTAuthentication
from .branch_scope import branch_q_for_ligne_sortie
from .openapi_params import PAGINATION_PARAMS, TAG_PORTAIL_CLIENT
from .permissions import IsClientAuthenticated
from .services.client_portal_achats import (
    achats_lignes_qs,
    achats_par_article,
    parse_achats_filters,
    serialize_achat_ligne,
)


def _openapi_fake_request(view) -> bool:
    return getattr(view, 'swagger_fake_view', False)


ACHATS_FILTER_PARAMS = PAGINATION_PARAMS + [
    openapi.Parameter('date_debut', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='YYYY-MM-DD'),
    openapi.Parameter('date_fin', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='YYYY-MM-DD'),
    openapi.Parameter('statut', openapi.IN_QUERY, type=openapi.TYPE_STRING, enum=['PAYEE', 'EN_CREDIT']),
    openapi.Parameter('article', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Code article ex. PRST0005'),
    openapi.Parameter('q', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Recherche nom article'),
]


class ClientPortalAchatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Historique des **achats d'articles** (lignes de vente) du client connecté.

    - ``GET /api/client-portal/achats/`` — liste chronologique paginée (une ligne = un article acheté)
    - ``GET /api/client-portal/achats/articles/`` — synthèse par article (totaux SQL)
    - ``GET /api/client-portal/achats/{id}/`` — détail d'une ligne d'achat
    """

    authentication_classes = [ClientJWTAuthentication]
    permission_classes = [IsClientAuthenticated]
    pagination_class = StandardResultsSetPagination
    queryset = LigneSortie.objects.none()

    def _membership_scope(self):
        return self.request.client, self.request.client_membership

    def _filters(self):
        try:
            return parse_achats_filters(self.request)
        except ValueError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': str(exc)}) from exc

    def get_queryset(self):
        if _openapi_fake_request(self):
            return LigneSortie.objects.none()
        client, m = self._membership_scope()
        return achats_lignes_qs(
            client=client,
            entreprise_id=m.entreprise_id,
            branch_q=branch_q_for_ligne_sortie(m),
            filters=self._filters(),
        )

    @swagger_auto_schema(
        operation_summary='Historique d\'achats (lignes)',
        manual_parameters=ACHATS_FILTER_PARAMS,
        tags=[TAG_PORTAIL_CLIENT],
    )
    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            data = [serialize_achat_ligne(l) for l in page]
            return self.get_paginated_response(data)
        data = [serialize_achat_ligne(l) for l in self.get_queryset()]
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        ligne = self.get_object()
        return Response(serialize_achat_ligne(ligne))

    @swagger_auto_schema(
        operation_summary='Mes achats par article (synthèse)',
        operation_description=(
            'Agrégation SQL par article : quantités totales, montants, nombre d\'achats, '
            'date du dernier achat. Performant pour afficher « produits que j\'ai déjà achetés ».'
        ),
        manual_parameters=ACHATS_FILTER_PARAMS,
        tags=[TAG_PORTAIL_CLIENT],
    )
    @action(detail=False, methods=['get'], url_path='articles')
    def articles(self, request):
        client, m = self._membership_scope()
        try:
            limit = min(max(1, int(request.query_params.get('limit', 100))), 500)
        except (TypeError, ValueError):
            limit = 100
        data = achats_par_article(
            client=client,
            entreprise_id=m.entreprise_id,
            branch_q=branch_q_for_ligne_sortie(m),
            filters=self._filters(),
            limit=limit,
        )
        return Response({
            'count': len(data),
            'results': data,
        })
