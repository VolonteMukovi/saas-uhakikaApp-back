from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from stock.inventaire_serializers import (
    InventaireDemarrerSerializer,
    InventaireLigneBulkSerializer,
    InventaireLigneSerializer,
    InventaireLigneUpdateSerializer,
    InventaireSessionCreateSerializer,
    InventaireSessionDetailSerializer,
    InventaireSessionListSerializer,
    InventaireSessionUpdateSerializer,
)
from stock.models import InventaireLigne, InventaireSession
from stock.permissions import IsAdminOrUser as StockIsAdminOrUser
from stock.services import inventaire as inventaire_service
from stock.views import TenantFilterMixin


class InventaireSessionViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    Sessions d'inventaire physique (stock théorique vs stock compté).

    Workflow :
    1. POST /inventaires/ — créer (option demarrer=true)
    2. POST /inventaires/{id}/demarrer/ — générer les lignes avec stock théorique figé
    3. PATCH /inventaires/{id}/lignes/{ligne_id}/ — saisir stock_physique
    4. POST /inventaires/{id}/lignes/bulk/ — saisie groupée
    5. POST /inventaires/{id}/valider/ — ajustements tracés (Entree/Sortie)
    6. POST /inventaires/{id}/annuler/ — annuler
    """
    queryset = InventaireSession.objects.all()
    permission_classes = [StockIsAdminOrUser]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('cree_par', 'valide_par', 'entree_ajustement', 'sortie_ajustement')
            .prefetch_related(
                'lignes__article__unite',
                'lignes__article__sous_type_article',
            )
            .order_by('-date_creation')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return InventaireSessionCreateSerializer
        if self.action in ('update', 'partial_update'):
            return InventaireSessionUpdateSerializer
        if self.action == 'retrieve':
            return InventaireSessionDetailSerializer
        return InventaireSessionListSerializer

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        session = serializer.instance
        session = self.get_queryset().get(pk=session.pk)
        return Response(
            InventaireSessionDetailSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.statut not in (
            InventaireSession.STATUT_BROUILLON,
            InventaireSession.STATUT_EN_COURS,
        ):
            return Response(
                {'detail': 'Cet inventaire ne peut plus être modifié.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.statut == InventaireSession.STATUT_VALIDE:
            return Response(
                {'detail': 'Un inventaire validé ne peut pas être supprimé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='demarrer')
    def demarrer(self, request, pk=None):
        session = self.get_object()
        ser = InventaireDemarrerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        inventaire_service.demarrer_session(
            session,
            article_ids=ser.validated_data.get('article_ids'),
        )
        session.refresh_from_db()
        return Response(
            InventaireSessionDetailSerializer(session).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['patch'], url_path=r'lignes/(?P<ligne_id>[^/.]+)')
    def modifier_ligne(self, request, pk=None, ligne_id=None):
        session = self.get_object()
        ligne = get_object_or_404(
            InventaireLigne.objects.select_related('article__unite'),
            pk=ligne_id,
            session=session,
        )
        ser = InventaireLigneUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        inventaire_service.mettre_a_jour_ligne(
            ligne,
            stock_physique=ser.validated_data['stock_physique'],
            motif_ligne=ser.validated_data.get('motif_ligne'),
        )
        ligne.refresh_from_db()
        return Response(InventaireLigneSerializer(ligne).data)

    @action(detail=True, methods=['post'], url_path='lignes/bulk')
    def bulk_lignes(self, request, pk=None):
        session = self.get_object()
        ser = InventaireLigneBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        updated = []
        errors = []
        for item in ser.validated_data['lignes']:
            try:
                ligne = InventaireLigne.objects.get(
                    session=session,
                    article_id=item['article_id'],
                )
                inventaire_service.mettre_a_jour_ligne(
                    ligne,
                    stock_physique=item['stock_physique'],
                    motif_ligne=item.get('motif_ligne', ''),
                )
                ligne.refresh_from_db()
                updated.append(InventaireLigneSerializer(ligne).data)
            except InventaireLigne.DoesNotExist:
                errors.append({
                    'article_id': item['article_id'],
                    'error': 'Article absent de cette session.',
                })
            except Exception as exc:
                errors.append({
                    'article_id': item['article_id'],
                    'error': str(exc),
                })
        payload = {
            'updated': updated,
            'errors': errors,
            'resume': inventaire_service.resume_session(session),
        }
        code = status.HTTP_200_OK if not errors else status.HTTP_207_MULTI_STATUS
        return Response(payload, status=code)

    @action(detail=True, methods=['post'], url_path='valider')
    def valider(self, request, pk=None):
        session = self.get_object()
        inventaire_service.valider_session(session, request.user)
        session.refresh_from_db()
        return Response(
            InventaireSessionDetailSerializer(session).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        session = self.get_object()
        inventaire_service.annuler_session(session)
        session.refresh_from_db()
        return Response(
            InventaireSessionDetailSerializer(session).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'], url_path='resume')
    def resume(self, request, pk=None):
        session = self.get_object()
        return Response({
            'session_id': session.pk,
            'statut': session.statut,
            'resume': inventaire_service.resume_session(session),
        })
