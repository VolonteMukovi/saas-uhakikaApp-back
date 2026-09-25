"""
Endpoints portail client : ventes en **lecture seule**, filtrées par client + entreprise
du JWT et par périmètre succursale (`branch_q_for_membership`).

Les commandes restent sur ``/api/commandes/`` (même auth JWT portail, règles CRUD inchangées).
"""
from django.db.models import Prefetch
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from config.pagination import StandardResultsSetPagination
from stock.models import LigneSortie, Sortie

from .authentication import ClientJWTAuthentication
from .branch_scope import branch_q_for_membership
from .client_portal_serializers import ClientPortalSortieReadSerializer
from .openapi_params import PAGINATION_PARAMS, TAG_PORTAIL_CLIENT
from .permissions import IsClientAuthenticated


def _openapi_fake_request(view) -> bool:
    """drf-yasg appelle get_queryset sans JWT : pas de request.client."""
    return getattr(view, "swagger_fake_view", False)


class ClientPortalSortieViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Ventes (sorties de stock) du client pour l'entreprise du JWT — lecture seule.
    """

    authentication_classes = [ClientJWTAuthentication]
    permission_classes = [IsClientAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = ClientPortalSortieReadSerializer

    def get_queryset(self):
        if _openapi_fake_request(self):
            return Sortie.objects.none()
        c = self.request.client
        m = self.request.client_membership
        bq = branch_q_for_membership(m)
        lignes_qs = LigneSortie.objects.select_related("article", "devise").order_by("id")
        return (
            Sortie.objects.filter(client=c, entreprise_id=m.entreprise_id)
            .filter(bq)
            .prefetch_related(Prefetch("lignes", queryset=lignes_qs))
            .order_by("-date_creation")
        )

    @swagger_auto_schema(
        operation_summary="Mes ventes (portail)",
        operation_description=(
            "Liste paginée des sorties (achats) du **client connecté** pour **l'entreprise du JWT**. "
            "Consultation uniquement — pas de création ni modification via cet endpoint."
        ),
        manual_parameters=PAGINATION_PARAMS,
        tags=[TAG_PORTAIL_CLIENT],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Détail d'une vente (portail)",
        operation_description="Sortie appartenant au client ; sinon 404.",
        tags=[TAG_PORTAIL_CLIENT],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
