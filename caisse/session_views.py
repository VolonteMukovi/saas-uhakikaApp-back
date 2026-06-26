"""
API sessions de caisse : ouverture, clôture, écarts, rapports.
"""
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from caisse.constants import CAISSE_DEFAUT_CODE
from caisse.models import EcartCaisse, SessionCaisse, TypeCaisse
from caisse.services.errors import validation_error_message
from caisse.services.session_active_state import build_active_state_response
from caisse.services.rapports_caisse import (
    build_mouvements_session_payload,
    build_rapport_detaille_session,
    build_rapport_general_session,
    parse_rapport_filtres_from_request,
)
from caisse.services.session_caisse import (
    SessionAlreadyOpenError,
    SessionCaisseError,
    calculer_totaux_session,
    cloturer_session_caisse,
    get_session_caisse_ouverte,
    ouvrir_session_caisse,
    valider_ecart_caisse,
)
from stock.serializers import DeviseSerializer
from stock.views import BusinessPermissionMixin, TenantFilterMixin
from users.permissions import IsAdminOrUser


class TypeCaisseMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeCaisse
        fields = ['id', 'nom', 'libelle', 'code_type', 'est_defaut']


class EcartCaisseSerializer(serializers.ModelSerializer):
    declare_par_nom = serializers.CharField(source='declare_par.username', read_only=True)
    valide_par_nom = serializers.CharField(source='valide_par.username', read_only=True)

    class Meta:
        model = EcartCaisse
        fields = [
            'id', 'session', 'type_ecart', 'montant', 'statut',
            'declare_par', 'declare_par_nom', 'valide_par', 'valide_par_nom',
            'valide_le', 'commentaire', 'mouvement_ajustement', 'cree_le',
        ]
        read_only_fields = fields


class SessionCaisseSerializer(serializers.ModelSerializer):
    type_caisse = TypeCaisseMinimalSerializer(read_only=True)
    devise = DeviseSerializer(read_only=True)
    ouvert_par_nom = serializers.CharField(source='ouvert_par.username', read_only=True)
    cloture_par_nom = serializers.CharField(source='cloture_par.username', read_only=True)
    ecart = EcartCaisseSerializer(read_only=True)
    totaux_courants = serializers.SerializerMethodField()

    class Meta:
        model = SessionCaisse
        fields = [
            'id', 'numero', 'type_caisse', 'devise', 'entreprise', 'succursale',
            'ouvert_par', 'ouvert_par_nom', 'cloture_par', 'cloture_par_nom',
            'ouvert_le', 'cloture_le', 'solde_ouverture', 'total_entrees', 'total_sorties',
            'solde_theorique', 'montant_physique', 'ecart_montant', 'statut',
            'commentaire_cloture', 'est_legacy', 'ecart', 'totaux_courants',
        ]
        read_only_fields = fields

    def get_totaux_courants(self, obj):
        if obj.statut == 'OUVERTE':
            t = calculer_totaux_session(obj)
            return {
                'total_entrees': str(t['total_entrees']),
                'total_sorties': str(t['total_sorties']),
                'solde_theorique': str(t['solde_theorique']),
                'nombre_mouvements': t['nombre_mouvements'],
            }
        return None


class OuvrirSessionCaisseSerializer(serializers.Serializer):
    type_caisse_id = serializers.IntegerField()
    devise_id = serializers.IntegerField()
    solde_ouverture = serializers.DecimalField(max_digits=14, decimal_places=5)


class CloturerSessionCaisseSerializer(serializers.Serializer):
    montant_physique = serializers.DecimalField(max_digits=14, decimal_places=5)
    commentaire = serializers.CharField(required=False, allow_blank=True, default='')


class ValiderEcartSerializer(serializers.Serializer):
    valider = serializers.BooleanField(default=True)
    commentaire = serializers.CharField(required=False, allow_blank=True, default='')


class SessionCaisseViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """
    Sessions de caisse — lecture, ouverture, clôture, validation écarts, rapports.
    """

    queryset = SessionCaisse.objects.all()
    serializer_class = SessionCaisseSerializer
    permission_classes = [IsAdminOrUser]

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'type_caisse', 'devise', 'ouvert_par', 'cloture_par', 'ecart',
            'ecart__valide_par', 'ecart__mouvement_ajustement',
        ).order_by('-ouvert_le', '-id')
        # Historique sessions : uniquement caisse cash physique par défaut
        qs = qs.filter(
            type_caisse__est_defaut=True,
            type_caisse__code_type=CAISSE_DEFAUT_CODE,
        )
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        devise_id = self.request.query_params.get('devise_id')
        if devise_id:
            qs = qs.filter(devise_id=devise_id)
        type_caisse_id = self.request.query_params.get('type_caisse_id') or self.request.query_params.get('caisse_id')
        if type_caisse_id:
            qs = qs.filter(type_caisse_id=type_caisse_id)
        date_debut = self.request.query_params.get('date_debut') or self.request.query_params.get('date_min')
        if date_debut:
            qs = qs.filter(ouvert_le__date__gte=date_debut)
        date_fin = self.request.query_params.get('date_fin') or self.request.query_params.get('date_max')
        if date_fin:
            qs = qs.filter(ouvert_le__date__lte=date_fin)
        utilisateur = self.request.query_params.get('utilisateur') or self.request.query_params.get('ouvert_par_id')
        if utilisateur:
            qs = qs.filter(ouvert_par_id=utilisateur)
        return qs

    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        """Session(s) ouverte(s) pour le contexte courant (format canonique ``is_open``)."""
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            return Response({'detail': _('Contexte entreprise manquant.')}, status=403)
        devise_id = request.query_params.get('devise_id')
        type_caisse_id = (
            request.query_params.get('type_caisse_id')
            or request.query_params.get('caisse_id')
        )
        if devise_id:
            try:
                session = get_session_caisse_ouverte(
                    tenant_id,
                    branch_id,
                    int(devise_id),
                    int(type_caisse_id) if type_caisse_id else None,
                )
            except SessionCaisseError as exc:
                return Response({'detail': validation_error_message(exc)}, status=400)
            if not session:
                return Response(build_active_state_response())
            session = SessionCaisse.objects.select_related(
                'type_caisse', 'devise', 'ouvert_par',
            ).get(pk=session.pk)
            return Response(build_active_state_response(session=session))

        qs = SessionCaisse.objects.filter(
            entreprise_id=tenant_id,
            statut='OUVERTE',
            type_caisse__est_defaut=True,
            type_caisse__code_type=CAISSE_DEFAUT_CODE,
        ).select_related('type_caisse', 'devise', 'ouvert_par')
        if branch_id is not None:
            qs = qs.filter(succursale_id=branch_id)
        if type_caisse_id:
            qs = qs.filter(type_caisse_id=int(type_caisse_id))
        sessions = list(qs.order_by('-ouvert_le', '-id'))
        if not sessions:
            return Response(build_active_state_response())
        return Response(build_active_state_response(session=sessions[0], sessions=sessions))

    @action(detail=False, methods=['post'], url_path='ouvrir')
    def ouvrir(self, request):
        ser = OuvrirSessionCaisseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            raise ValidationError({'detail': _('Contexte entreprise manquant.')})
        try:
            session = ouvrir_session_caisse(
                entreprise_id=tenant_id,
                succursale_id=branch_id,
                type_caisse_id=ser.validated_data['type_caisse_id'],
                devise_id=ser.validated_data['devise_id'],
                solde_ouverture=ser.validated_data['solde_ouverture'],
                utilisateur=request.user,
            )
        except SessionAlreadyOpenError as exc:
            existing = SessionCaisse.objects.select_related(
                'type_caisse', 'devise', 'ouvert_par',
            ).get(pk=exc.session.pk)
            payload = build_active_state_response(session=existing)
            payload['code'] = 'SESSION_ALREADY_OPEN'
            payload['detail'] = validation_error_message(exc)
            return Response(payload, status=status.HTTP_409_CONFLICT)
        except SessionCaisseError as exc:
            raise ValidationError({'detail': validation_error_message(exc)}) from exc
        return Response(
            SessionCaisseSerializer(session, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='cloturer')
    def cloturer(self, request, pk=None):
        session = self.get_object()
        ser = CloturerSessionCaisseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            session = cloturer_session_caisse(
                session=session,
                montant_physique=ser.validated_data['montant_physique'],
                utilisateur=request.user,
                commentaire=ser.validated_data.get('commentaire', ''),
            )
        except SessionCaisseError as exc:
            raise ValidationError({'detail': validation_error_message(exc)}) from exc
        session = SessionCaisse.objects.select_related('ecart').get(pk=session.pk)
        return Response(SessionCaisseSerializer(session, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='valider-ecart', permission_classes=[IsAdminOrUser])
    def valider_ecart(self, request, pk=None):
        if not request.user.is_admin(request):
            raise PermissionDenied(_('Seul un administrateur peut valider un écart de caisse.'))
        session = self.get_object()
        if not hasattr(session, 'ecart'):
            raise ValidationError({'detail': _('Aucun écart en attente pour cette session.')})
        ser = ValiderEcartSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ecart = valider_ecart_caisse(
                ecart=session.ecart,
                administrateur=request.user,
                valider=ser.validated_data['valider'],
                commentaire=ser.validated_data.get('commentaire', ''),
            )
        except SessionCaisseError as exc:
            raise ValidationError({'detail': validation_error_message(exc)}) from exc
        session.refresh_from_db()
        return Response({
            'session': SessionCaisseSerializer(session, context={'request': request}).data,
            'ecart': EcartCaisseSerializer(ecart).data,
        })

    @action(detail=True, methods=['get'], url_path='rapport-general')
    def rapport_general(self, request, pk=None):
        session = self.get_object()
        return Response(build_rapport_general_session(session))

    @action(detail=True, methods=['get'], url_path='rapport-detaille')
    def rapport_detaille(self, request, pk=None):
        session = self.get_object()
        filtres = parse_rapport_filtres_from_request(request)
        return Response(build_rapport_detaille_session(session, filtres))

    @action(detail=True, methods=['get'], url_path='mouvements')
    def mouvements(self, request, pk=None):
        """Mouvements de la session uniquement (JSON, tous statuts)."""
        session = self.get_object()
        filtres = parse_rapport_filtres_from_request(request)
        return Response(build_mouvements_session_payload(session, filtres))

    @action(detail=True, methods=['get'], url_path='proces-verbal')
    def proces_verbal(self, request, pk=None):
        """Procès-verbal de clôture (JSON structuré — PDF côté frontend)."""
        session = self.get_object()
        totaux = calculer_totaux_session(session)
        ecart_data = None
        if hasattr(session, 'ecart'):
            ecart_data = EcartCaisseSerializer(session.ecart).data
        return Response({
            'document': 'proces_verbal_cloture_caisse',
            'titre': _('Procès-verbal de clôture de caisse'),
            'session': SessionCaisseSerializer(session, context={'request': request}).data,
            'totaux': {
                'solde_ouverture': str(session.solde_ouverture),
                'total_entrees': str(totaux['total_entrees']),
                'total_sorties': str(totaux['total_sorties']),
                'solde_theorique': str(totaux['solde_theorique']),
                'montant_physique': str(session.montant_physique or ''),
                'ecart': str(session.ecart_montant or '0'),
            },
            'ecart': ecart_data,
            'genere_le': timezone.now().isoformat(),
        })
