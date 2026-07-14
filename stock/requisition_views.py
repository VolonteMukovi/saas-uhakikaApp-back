from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from stock.models import Article, Requisition, RequisitionLigne
from stock.permissions import IsAdminOrUser as StockIsAdminOrUser
from stock.requisition_serializers import (
    RequisitionCreateSerializer,
    RequisitionDetailSerializer,
    RequisitionListSerializer,
    RequisitionLigneUpdateSerializer,
    RequisitionLigneWriteSerializer,
    RequisitionReorderSerializer,
    RequisitionStatutSerializer,
    RequisitionSuggestionsSerializer,
    RequisitionUpdateSerializer,
)
from stock.services import requisition as requisition_service
from stock.services.requisition_document import build_requisition_document
from stock.views import TenantFilterMixin


class RequisitionViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    CRUD professionnel des réquisitions d'approvisionnement.

    Workflow :
    1. POST /requisitions/ — créer (option avec_suggestions)
    2. POST /requisitions/{id}/lignes/ — ajouter article ou ligne libre
    3. POST /requisitions/{id}/suggestions/ — injecter rupture/alerte/expiration
    4. PATCH lignes, reorder, dupliquer
    5. POST .../soumettre/ | valider/ | rejeter/ | cloturer/
    6. GET .../document/ — JSON d'impression (PDF généré côté frontend)
    """

    queryset = Requisition.objects.all()
    permission_classes = [StockIsAdminOrUser]
    filterset_fields = []  # filtrage manuel dans list()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('cree_par', 'valide_par', 'rejete_par', 'succursale', 'entreprise')
            .prefetch_related('lignes__article__unite', 'historique__utilisateur')
            .order_by('-date_creation')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return RequisitionCreateSerializer
        if self.action in ('update', 'partial_update'):
            return RequisitionUpdateSerializer
        if self.action == 'retrieve':
            return RequisitionDetailSerializer
        return RequisitionListSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        params = request.query_params

        statut = params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        priorite = params.get('priorite')
        if priorite:
            qs = qs.filter(priorite=priorite)
        cree_par = params.get('cree_par') or params.get('utilisateur')
        if cree_par:
            qs = qs.filter(cree_par_id=cree_par)
        succursale = params.get('succursale') or params.get('succursale_id')
        if succursale:
            qs = qs.filter(succursale_id=succursale)
        archived = params.get('archived')
        if archived is not None:
            flag = str(archived).lower() in ('1', 'true', 'yes', 'oui')
            qs = qs.filter(archived=flag)

        date_from = params.get('date_from') or params.get('date_debut')
        date_to = params.get('date_to') or params.get('date_fin')
        if date_from:
            qs = qs.filter(date_creation__date__gte=date_from)
        if date_to:
            qs = qs.filter(date_creation__date__lte=date_to)

        search = (params.get('search') or params.get('q') or '').strip()
        if search:
            qs = qs.filter(
                Q(numero__icontains=search)
                | Q(titre__icontains=search)
                | Q(description__icontains=search)
                | Q(observations__icontains=search)
                | Q(lignes__designation__icontains=search)
            ).distinct()

        page = self.paginate_queryset(qs)
        ser = RequisitionListSerializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = serializer.save()
        req = self.get_queryset().get(pk=req.pk)
        return Response(
            RequisitionDetailSerializer(req).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        req = serializer.save()
        req = self.get_queryset().get(pk=req.pk)
        return Response(RequisitionDetailSerializer(req).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.statut not in (
            Requisition.STATUT_BROUILLON,
            Requisition.STATUT_ANNULEE,
        ):
            return Response(
                {'detail': 'Seuls les brouillons ou annulations peuvent être supprimés.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    def _detail(self, requisition):
        requisition = self.get_queryset().get(pk=requisition.pk)
        return Response(RequisitionDetailSerializer(requisition).data)

    def _transition(self, request, nouveau_statut):
        requisition = self.get_object()
        ser = RequisitionStatutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user if request.user.is_authenticated else None
        requisition_service.changer_statut(
            requisition,
            nouveau_statut=nouveau_statut,
            utilisateur=user,
            motif=ser.validated_data.get('motif') or '',
            commentaires=ser.validated_data.get('commentaires') or '',
        )
        return self._detail(requisition)

    @action(detail=False, methods=['get'], url_path='suggestions-preview')
    def suggestions_preview(self, request):
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            return Response({'detail': 'Contexte entreprise manquant.'}, status=400)
        sources = request.query_params.getlist('sources') or request.query_params.get('sources')
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.split(',') if s.strip()]
        if not sources:
            sources = ['rupture', 'alerte']
        rows = requisition_service.preview_suggestions(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            sources=sources,
        )
        return Response({'count': len(rows), 'suggestions': rows})

    @action(detail=True, methods=['post'], url_path='suggestions')
    def suggestions(self, request, pk=None):
        requisition = self.get_object()
        ser = RequisitionSuggestionsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = requisition_service.apply_suggestions(
            requisition,
            sources=ser.validated_data.get('sources') or ['rupture', 'alerte'],
            utilisateur=request.user if request.user.is_authenticated else None,
            replace=bool(ser.validated_data.get('replace')),
        )
        data = RequisitionDetailSerializer(self.get_queryset().get(pk=requisition.pk)).data
        data['suggestions_result'] = result
        return Response(data)

    @action(detail=True, methods=['post'], url_path='lignes')
    def add_ligne(self, request, pk=None):
        requisition = self.get_object()
        ser = RequisitionLigneWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        user = request.user if request.user.is_authenticated else None
        type_ligne = data.get('type_ligne') or RequisitionLigne.TYPE_ARTICLE
        if type_ligne == RequisitionLigne.TYPE_LIBRE:
            requisition_service.add_ligne_libre(
                requisition,
                designation=data.get('designation') or '',
                quantite=data['quantite'],
                unite=data.get('unite') or '',
                prix_estime=data.get('prix_estime'),
                remarque=data.get('remarque') or '',
                utilisateur=user,
            )
        else:
            article = get_object_or_404(
                Article,
                article_id=data['article_id'],
                entreprise_id=requisition.entreprise_id,
            )
            requisition_service.add_ligne_article(
                requisition,
                article,
                quantite=data.get('quantite'),
                unite=data.get('unite'),
                prix_estime=data.get('prix_estime'),
                remarque=data.get('remarque') or '',
                utilisateur=user,
            )
        return self._detail(requisition)

    @action(
        detail=True,
        methods=['patch', 'delete', 'post'],
        url_path=r'lignes/(?P<ligne_id>[0-9]+)',
    )
    def ligne_detail(self, request, pk=None, ligne_id=None):
        requisition = self.get_object()
        ligne = get_object_or_404(RequisitionLigne, pk=ligne_id, requisition=requisition)
        user = request.user if request.user.is_authenticated else None

        if request.method == 'DELETE':
            requisition_service.delete_ligne(ligne, utilisateur=user)
            return self._detail(requisition)

        if request.method == 'POST':
            # Dupliquer : POST .../lignes/{id}/ avec {"action":"dupliquer"} ou url dupliquer
            action_name = (request.data.get('action') or 'dupliquer').lower()
            if action_name != 'dupliquer':
                return Response({'detail': 'Action non supportée.'}, status=400)
            requisition_service.dupliquer_ligne(ligne, utilisateur=user)
            return self._detail(requisition)

        ser = RequisitionLigneUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        requisition_service.update_ligne(ligne, data=ser.validated_data, utilisateur=user)
        return self._detail(requisition)

    @action(detail=True, methods=['post'], url_path=r'lignes/(?P<ligne_id>[0-9]+)/dupliquer')
    def dupliquer_ligne(self, request, pk=None, ligne_id=None):
        requisition = self.get_object()
        ligne = get_object_or_404(RequisitionLigne, pk=ligne_id, requisition=requisition)
        requisition_service.dupliquer_ligne(
            ligne,
            utilisateur=request.user if request.user.is_authenticated else None,
        )
        return self._detail(requisition)

    @action(detail=True, methods=['post'], url_path='reordonner')
    def reordonner(self, request, pk=None):
        requisition = self.get_object()
        ser = RequisitionReorderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        requisition_service.reorder_lignes(
            requisition,
            ser.validated_data['ordre'],
            utilisateur=request.user if request.user.is_authenticated else None,
        )
        return self._detail(requisition)

    @action(detail=True, methods=['post'], url_path='ouvrir')
    def ouvrir(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_OUVERTE)

    @action(detail=True, methods=['post'], url_path='preparer')
    def preparer(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_EN_PREPARATION)

    @action(detail=True, methods=['post'], url_path='soumettre')
    def soumettre(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_EN_ATTENTE_VALIDATION)

    @action(detail=True, methods=['post'], url_path='valider')
    def valider(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_VALIDEE)

    @action(detail=True, methods=['post'], url_path='rejeter')
    def rejeter(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_REJETEE)

    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_ANNULEE)

    @action(detail=True, methods=['post'], url_path='cloturer')
    def cloturer(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_CLOTUREE)

    @action(detail=True, methods=['post'], url_path='reouvrir')
    def reouvrir(self, request, pk=None):
        return self._transition(request, Requisition.STATUT_BROUILLON)

    @action(detail=True, methods=['get'], url_path='document')
    def document(self, request, pk=None):
        """JSON complet pour impression / export PDF côté frontend."""
        requisition = self.get_object()
        return Response(build_requisition_document(requisition, request=request))

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        """
        Alias rétrocompatible de ``document``.
        Ne renvoie plus de binaire PDF — uniquement du JSON métier.
        """
        return self.document(request, pk=pk)
