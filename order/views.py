from django.db.models import Prefetch
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from config.pagination import StandardResultsSetPagination
from users.permissions import IsAdmin

from .filters import (
    apply_fournisseur_filters,
    apply_frais_lot_filters,
    apply_lot_filters,
    apply_lot_item_filters,
    apply_ordering,
)
from .mixins import filter_by_tenant
from .models import Fournisseur, FraisLot, Lot, LotItem
from .openapi_params import (
    FOURNISSEUR_LIST_PARAMS,
    FRAIS_LOT_LIST_PARAMS,
    LOT_CREATE_DESCRIPTION,
    LOT_ITEM_LIST_PARAMS,
    LOT_LIST_PARAMS,
    LOT_RETRIEVE_DESCRIPTION,
    LOT_UPDATE_DESCRIPTION,
    TAG_FOURNISSEUR,
    TAG_TRANSIT,
)
from .serializers import (
    FraisLotSerializer,
    FournisseurSerializer,
    LotItemSerializer,
    LotSerializer,
)


class AdminTenantViewSet(viewsets.ModelViewSet):
    """
    CRUD réservé aux **administrateurs d'entreprise** (`Membership.role=admin`).
    Les **agents** n'ont pas accès aux lots en transit ni aux fournisseurs achats.
    Pagination : `StandardResultsSetPagination` (paramètres `page`, `page_size`).
    """

    permission_classes = [IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_by_tenant(qs, self.request)


class FournisseurViewSet(AdminTenantViewSet):
    """
    Référentiel fournisseurs (multi-tenant).

    **Permissions** : administrateur uniquement (pas les agents).
    """

    queryset = Fournisseur.objects.all().select_related("entreprise", "succursale")
    serializer_class = FournisseurSerializer

    @swagger_auto_schema(
        operation_summary="Liste des fournisseurs",
        operation_description=(
            "Liste paginée, filtrée par entreprise (et succursale JWT si applicable). "
            "Recherche texte via `search` ou `q`."
        ),
        manual_parameters=FOURNISSEUR_LIST_PARAMS,
        tags=[TAG_FOURNISSEUR],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_fournisseur_filters(qs, self.request)
        ordering_allowed = {
            "nom": "nom",
            "code": "code",
            "created_at": "created_at",
            "id": "id",
        }
        return apply_ordering(qs, self.request, ordering_allowed, "-created_at")


class LotViewSet(AdminTenantViewSet):
    """
    Lots de marchandises en transit.

    **Permissions** : administrateur uniquement.
    Filtres courants : `fournisseur_id`, `statut`, plages de dates, `reference`, `search`.

    **Clôture (`statut=CLOTURE`)** : aucune entrée en stock tant que le lot n'est pas clôturé.
    Au passage à `CLOTURE`, envoyer le corps **`approvisionnement`** (une entrée par article :
    `article_id`, `prix_vente`, `seuil_alerte`, `date_expiration` optionnelle). Ces champs ne sont
    pas stockés sur les lignes de lot ; ils alimentent uniquement les **`LigneEntree`** créées.
    Réponse : `entree_stock`, mise à jour des stocks (aucun mouvement de caisse à la clôture).

    **Lots `ARRIVE` ou `CLOTURE`** : plus de modification ni suppression du lot (sauf passage
    `ARRIVE` → `CLOTURE` avec `approvisionnement`). Lignes de lot et frais : pas de création /
    modification / suppression après l'arrivée du lot.
    """

    queryset = Lot.objects.all().select_related(
        "entreprise", "succursale", "fournisseur", "entree_stock"
    )
    serializer_class = LotSerializer

    @swagger_auto_schema(
        operation_summary="Liste des lots en transit",
        operation_description=(
            "Recherche performante par **fournisseur** (`fournisseur_id`) et par texte (`search` : "
            "référence du lot, nom ou code fournisseur). Indexation côté base sur "
            "`entreprise` + `fournisseur`, `statut`, `date_expedition`."
        ),
        manual_parameters=LOT_LIST_PARAMS,
        tags=[TAG_TRANSIT],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Créer un lot",
        operation_description=LOT_CREATE_DESCRIPTION,
        tags=[TAG_TRANSIT],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Détail d'un lot",
        operation_description=LOT_RETRIEVE_DESCRIPTION,
        tags=[TAG_TRANSIT],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Mise à jour d'un lot (PUT)",
        operation_description=LOT_UPDATE_DESCRIPTION,
        tags=[TAG_TRANSIT],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Mise à jour partielle d'un lot (PATCH)",
        operation_description=LOT_UPDATE_DESCRIPTION,
        tags=[TAG_TRANSIT],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Supprimer un lot",
        operation_description=(
            "Suppression définitive du lot **uniquement** s’il n’est pas **ARRIVE**, **CLOTURE** "
            "ou déjà lié à une **entrée en stock**. Même ressource que GET / PUT / PATCH sur "
            "`/api/lots/{id}/` — toutes les méthodes HTTP du détail sont documentées dans Swagger / ReDoc."
        ),
        tags=[TAG_TRANSIT],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if instance.statut in (Lot.StatutLot.ARRIVE, Lot.StatutLot.CLOTURE) or instance.entree_stock_id:
            raise ValidationError(
                "Impossible de supprimer un lot arrivé, clôturé ou déjà lié à une entrée en stock."
            )
        super().perform_destroy(instance)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_lot_filters(qs, self.request)
        ordering_allowed = {
            "created_at": "created_at",
            "date_expedition": "date_expedition",
            "reference": "reference",
            "statut": "statut",
            "id": "id",
        }
        qs = apply_ordering(qs, self.request, ordering_allowed, "-created_at")
        if getattr(self, "action", None) in ("retrieve", "update", "partial_update"):
            qs = qs.prefetch_related(
                Prefetch(
                    "items",
                    queryset=LotItem.objects.select_related("article"),
                ),
                "frais",
            )
        return qs


class FraisLotViewSet(AdminTenantViewSet):
    """Frais associés à un lot (transport, douane, manutention). Administrateur uniquement."""

    queryset = FraisLot.objects.all().select_related("entreprise", "succursale", "lot", "devise")
    serializer_class = FraisLotSerializer

    @swagger_auto_schema(
        operation_summary="Liste des frais de lot",
        manual_parameters=FRAIS_LOT_LIST_PARAMS,
        tags=[TAG_TRANSIT],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_frais_lot_filters(qs, self.request)
        ordering_allowed = {
            "created_at": "created_at",
            "montant": "montant",
            "type_frais": "type_frais",
            "id": "id",
        }
        return apply_ordering(qs, self.request, ordering_allowed, "-created_at")

    def perform_destroy(self, instance):
        if instance.lot.statut in (Lot.StatutLot.ARRIVE, Lot.StatutLot.CLOTURE):
            raise ValidationError(
                "Impossible de supprimer des frais : le lot est arrivé ou clôturé."
            )
        super().perform_destroy(instance)


class LotItemViewSet(AdminTenantViewSet):
    """Contenu d'un lot (articles + quantités + PU achat). Administrateur uniquement."""

    queryset = LotItem.objects.all().select_related("entreprise", "succursale", "lot", "article")
    serializer_class = LotItemSerializer

    @swagger_auto_schema(
        operation_summary="Liste des lignes de lot",
        manual_parameters=LOT_ITEM_LIST_PARAMS,
        tags=[TAG_TRANSIT],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance):
        lot = instance.lot
        if lot.statut in (Lot.StatutLot.ARRIVE, Lot.StatutLot.CLOTURE) or lot.entree_stock_id:
            raise ValidationError(
                "Impossible de supprimer une ligne d'un lot arrivé ou clôturé."
            )
        super().perform_destroy(instance)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = apply_lot_item_filters(qs, self.request)
        ordering_allowed = {
            "created_at": "created_at",
            "quantite": "quantite",
            "prix_achat_unitaire": "prix_achat_unitaire",
            "id": "id",
        }
        return apply_ordering(qs, self.request, ordering_allowed, "-created_at")
