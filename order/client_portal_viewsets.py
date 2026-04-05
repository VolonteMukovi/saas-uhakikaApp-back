"""
Endpoints portail client : dettes et ventes en **lecture seule**, filtrées par client + entreprise
du JWT et par périmètre succursale (`branch_q_for_membership`).

Les commandes restent sur ``/api/commandes/`` (même auth JWT portail, règles CRUD inchangées).
"""
from django.db.models import Prefetch
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.pagination import StandardResultsSetPagination
from stock.models import DetteClient, LigneSortie, Sortie
from stock.serializers import DetteClientSerializer, PaiementDetteReadSerializer

from .authentication import ClientJWTAuthentication
from .branch_scope import branch_q_for_membership
from .client_portal_serializers import ClientPortalSortieReadSerializer
from .openapi_params import PAGINATION_PARAMS, TAG_PORTAIL_CLIENT
from .permissions import IsClientAuthenticated


def _openapi_fake_request(view) -> bool:
    """drf-yasg appelle get_queryset sans JWT : pas de request.client."""
    return getattr(view, "swagger_fake_view", False)


class ClientPortalDetteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Dettes du client connecté pour l'entreprise du JWT (succursale du membership).

    **Aucune** création, mise à jour ni suppression — consultation uniquement.
    """

    authentication_classes = [ClientJWTAuthentication]
    permission_classes = [IsClientAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = DetteClientSerializer

    def get_queryset(self):
        if _openapi_fake_request(self):
            return DetteClient.objects.none()
        c = self.request.client
        m = self.request.client_membership
        bq = branch_q_for_membership(m)
        return (
            DetteClient.objects.filter(client=c, entreprise_id=m.entreprise_id)
            .filter(bq)
            .select_related("client", "devise", "sortie")
            .order_by("-date_creation", "-id")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        # Liste : alléger (pas d'historique paiements embarqué) ; détail : complet.
        ctx["include_paiements"] = self.action != "list"
        return ctx

    @swagger_auto_schema(
        operation_summary="Mes dettes (portail)",
        operation_description=(
            "Liste paginée des dettes du **client connecté** pour **l'entreprise du JWT** "
            "et le périmètre succursale du lien. Aucune donnée d'un autre client."
        ),
        manual_parameters=PAGINATION_PARAMS,
        tags=[TAG_PORTAIL_CLIENT],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Détail d'une dette (portail)",
        operation_description="Dette appartenant au client ; sinon 404.",
        tags=[TAG_PORTAIL_CLIENT],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Paiements enregistrés sur cette dette (portail)",
        operation_description="Historique des encaissements liés à la dette (pagination identique à la liste).",
        manual_parameters=PAGINATION_PARAMS,
        tags=[TAG_PORTAIL_CLIENT],
    )
    @action(detail=True, methods=["get"], url_path="paiements")
    def paiements(self, request, pk=None):
        dette = self.get_object()
        paiements_qs = (
            dette._paiements_mouvements_qs()
            .select_related("devise", "utilisateur")
            .prefetch_related("details__type_caisse")
            .order_by("-date", "-id")
        )
        page = self.paginate_queryset(paiements_qs)
        if page is not None:
            serializer = PaiementDetteReadSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = PaiementDetteReadSerializer(paiements_qs, many=True, context={"request": request})
        return Response(serializer.data)


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
