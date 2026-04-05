from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from config.pagination import StandardResultsSetPagination
from stock.services.tenant_context import get_tenant_ids
from users.authentication import JWTAuthenticationWithContext

from .authentication import ClientJWTAuthentication
from .branch_scope import apply_admin_commande_branch_filter, branch_q_for_membership
from .commande_filters import apply_commande_filters, apply_commande_ordering
from .commande_serializers import (
    CommandeClientUpdateSerializer,
    CommandeCreateSerializer,
    CommandeDetailSerializer,
    CommandeListSerializer,
    CommandeResponseCreateSerializer,
    CommandeResponseSerializer,
    CommandeResponseUpdateSerializer,
    CommandeUpdateAdminSerializer,
)
from .models import Commande, CommandeResponse
from .openapi_params import COMMANDE_LIST_PARAMS, COMMANDE_UPDATE_REQUEST_BODY, TAG_COMMANDE
from .permissions import (
    IsAdminOrClientDestroyCommande,
    IsStaffEntrepriseForCommandes,
    IsStaffOrClientCommande,
)


class CommandeViewSet(viewsets.ModelViewSet):
    """
    Commandes clients (portail + back-office).

    - **Client** (JWT portail) : CRUD sur **ses** commandes ; modification / suppression uniquement si **en attente**.
    - **Administrateur** : toutes les commandes ; mise à jour limitée au **statut** (rejetée / livrée).
    - **Employé (agent)** : consultation et mise à jour du **statut** (rejetée / livrée) ; pas de suppression.
    """

    # IMPORTANT: L'ordre compte.
    # Si le JWT staff est tenté en premier, un JWT portail (sans "user id") est rejeté avant
    # que l'auth portail n'ait sa chance → boucle côté frontend (401 puis redirection login).
    authentication_classes = [ClientJWTAuthentication, JWTAuthenticationWithContext]
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminOrClientDestroyCommande()]
        return [IsStaffOrClientCommande()]

    def get_queryset(self):
        qs = (
            Commande.objects.all()
            .select_related("client", "entreprise", "succursale")
            .prefetch_related("items__article__sous_type_article__type_article", "items__article__unite", "reponses__auteur")
        )
        request = self.request
        if getattr(request, "client", None):
            c = request.client
            m = request.client_membership
            bq = branch_q_for_membership(m)
            qs = qs.filter(client_id=c.pk, entreprise_id=m.entreprise_id).filter(bq)
        else:
            tenant_id, branch_id = get_tenant_ids(request)
            qs = apply_admin_commande_branch_filter(qs, request, tenant_id, branch_id)
        qs = apply_commande_filters(qs, request)
        return apply_commande_ordering(qs, request)

    def get_serializer_class(self):
        if self.action == "create":
            return CommandeCreateSerializer
        if self.action in ("update", "partial_update"):
            request = self.request
            if getattr(request, "client", None):
                return CommandeClientUpdateSerializer
            return CommandeUpdateAdminSerializer
        if self.action == "list":
            return CommandeListSerializer
        return CommandeDetailSerializer

    def perform_destroy(self, instance):
        if getattr(self.request, "client", None):
            if instance.statut != Commande.StatutCommande.EN_ATTENTE:
                raise PermissionDenied(_("Seules les commandes en attente peuvent être supprimées."))
        instance.delete()

    @swagger_auto_schema(
        operation_summary="Liste des commandes",
        operation_description=(
            "**Client** : uniquement ses commandes (JWT portail). "
            "**Administrateur** : commandes du périmètre **entreprise** ; si le contexte JWT fixe une **succursale** "
            "(ou ``?succursale_id=``), liste filtrée en conséquence. "
            "**Employé (agent)** : même périmètre que l’admin pour la liste (statut / filtre succursale). "
            "Filtres et recherche documentés ci-dessous ; pagination `page` / `page_size`."
        ),
        manual_parameters=COMMANDE_LIST_PARAMS,
        tags=[TAG_COMMANDE],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Détail d’une commande",
        operation_description=(
            "Client : sa commande, **même périmètre succursale** que le portail. "
            "Admin : commande visible selon entreprise + succursale JWT / filtre."
        ),
        tags=[TAG_COMMANDE],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Créer une commande",
        operation_description=(
            "**Client** : ne pas envoyer `client_id` (déduit du token). Corps : `items` (obligatoire), "
            "`nom` et `note_client` optionnels, `succursale` optionnelle. Chaque ligne : `article_id` **ou** "
            "`nom_article`, jamais les deux, jamais aucun des deux ; `quantite` ≥ 1.\n\n"
            "**Admin** : `client_id` obligatoire (client de la même entreprise). "
            "La succursale de la commande suit le **contexte JWT** (succursale courante), "
            "le corps (`succursale`) ou le client cible — voir validateur."
        ),
        request_body=CommandeCreateSerializer,
        responses={201: CommandeDetailSerializer},
        tags=[TAG_COMMANDE],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commande = serializer.save()
        out = CommandeDetailSerializer(commande, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Mise à jour complète",
        operation_description=(
            "Schéma ci-dessous regroupe **deux variantes** (client portail vs staff) ; l’API n’accepte "
            "que celle qui correspond au JWT.\n\n"
            "**Client** : `nom`, `note_client`, `succursale`, `items` ; uniquement si **EN_ATTENTE**.\n\n"
            "**Admin / employé** : **`statut`** = **REJETEE** ou **LIVREE** uniquement. "
            "**LIVREE** déclenche une sortie de stock (FIFO) pour les quantités commandées, comme une vente."
        ),
        request_body=COMMANDE_UPDATE_REQUEST_BODY,
        responses={200: CommandeDetailSerializer},
        tags=[TAG_COMMANDE],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Mise à jour partielle",
        operation_description=(
            "Même logique que PUT : corps selon **JWT portail** (client) ou **JWT staff** ; "
            "seuls les champs pertinents sont envoyés."
        ),
        request_body=COMMANDE_UPDATE_REQUEST_BODY,
        responses={200: CommandeDetailSerializer},
        tags=[TAG_COMMANDE],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Supprimer une commande",
        operation_description=(
            "**Client** : suppression autorisée uniquement si la commande est **en attente**.\n\n"
            "**Administrateur** : suppression autorisée (employé : 403)."
        ),
        tags=[TAG_COMMANDE],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Ajouter une réponse officielle (suivi / validation)",
        operation_description="POST sur une commande : commentaire de suivi ; `auteur` = utilisateur staff connecté.",
        request_body=CommandeResponseCreateSerializer,
        responses={201: CommandeResponseSerializer},
        tags=[TAG_COMMANDE],
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="reponses",
        permission_classes=[IsStaffEntrepriseForCommandes],
    )
    def add_reponse(self, request, pk=None):
        commande = self.get_object()
        ser = CommandeResponseCreateSerializer(data=request.data, context={"request": request, "commande": commande})
        ser.is_valid(raise_exception=True)
        r = ser.save()
        return Response(CommandeResponseSerializer(r, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method="patch",
        operation_summary="Modifier une réponse à la commande",
        operation_description=(
            "**Administrateur ou employé** : met à jour le **commentaire** ; `auteur` et `created_at` ne changent pas."
        ),
        request_body=CommandeResponseUpdateSerializer,
        responses={200: CommandeResponseSerializer},
        tags=[TAG_COMMANDE],
    )
    @swagger_auto_schema(
        method="delete",
        operation_summary="Supprimer une réponse à la commande",
        operation_description="**Administrateur ou employé** : supprime cette réponse (liée à la commande indiquée).",
        responses={204: openapi.Response(description="Réponse supprimée, sans corps.")},
        tags=[TAG_COMMANDE],
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"reponses/(?P<reponse_id>[^/.]+)",
        permission_classes=[IsStaffEntrepriseForCommandes],
    )
    def reponse_commande_detail(self, request, pk=None, reponse_id=None):
        commande = self.get_object()
        reponse = get_object_or_404(CommandeResponse, pk=reponse_id, commande=commande)
        if request.method == "DELETE":
            reponse.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = CommandeResponseUpdateSerializer(
            reponse,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        ser.is_valid(raise_exception=True)
        reponse = ser.save()
        return Response(CommandeResponseSerializer(reponse, context={"request": request}).data)
