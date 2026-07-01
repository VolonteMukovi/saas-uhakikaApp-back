from django.utils.translation import gettext as _
from django.db.models import Count, Sum
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from abonnements.models import (
    AbonnementEntreprise,
    DemandeInstallationPrivee,
    FormuleAbonnement,
    JournalActivationLicence,
)
from abonnements.permissions import AEntrepriseContexte, EstSuperAdminPlateforme
from abonnements.serializers import (
    AbonnementEntrepriseSerializer,
    ActivationManuelleParEntrepriseSerializer,
    ActivationManuelleSerializer,
    DemandeAbonnementSerializer,
    DemandeInstallationPriveeSerializer,
    EtatLicenceSerializer,
    FormuleAbonnementSerializer,
    JournalActivationLicenceSerializer,
    PlateformeAbonnementSerializer,
    ResumeLimitesSerializer,
)
from abonnements.services.licence import (
    activer_abonnement_manuellement,
    activer_abonnement_pour_entreprise,
    build_etat_licence,
    demander_abonnement,
    get_abonnement_courant,
)
from abonnements.services.limites import build_resume_limites
from inscription.services.bootstrap_saas import assurer_contexte_initial_utilisateur

MESSAGE_INSTALLATION_PRIVEE = (
    'UHAKIKAAPP fonctionne principalement comme une solution SaaS accessible en ligne. '
    'Pour les entreprises souhaitant une installation privée ou locale, une étude spéciale '
    'peut être effectuée avec l\'équipe technique. Le coût dépendra des besoins, de '
    'l\'infrastructure, du nombre de postes, du niveau de personnalisation, de la formation '
    'et de la maintenance souhaitée.'
)


class FormuleAbonnementViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogue public des formules payantes."""
    serializer_class = FormuleAbonnementSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return FormuleAbonnement.objects.filter(
            est_active=True,
            est_visible_catalogue=True,
        ).order_by('ordre_affichage')


class MonAbonnementView(APIView):
    """État de l'abonnement / licence de l'entreprise courante."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: EtatLicenceSerializer()})
    def get(self, request):
        assurer_contexte_initial_utilisateur(request.user)
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        if not eid:
            return Response(
                {'detail': _('Préparation de votre espace en cours. Réessayez dans quelques secondes.')},
                status=status.HTTP_409_CONFLICT,
            )
        etat = build_etat_licence(eid)
        return Response(EtatLicenceSerializer(etat).data)


class MesLimitesView(APIView):
    """Quotas et fonctionnalités du plan courant (pour le frontend)."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: ResumeLimitesSerializer()})
    def get(self, request):
        assurer_contexte_initial_utilisateur(request.user)
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        if not eid:
            return Response(
                {'detail': _('Préparation de votre espace en cours. Réessayez dans quelques secondes.')},
                status=status.HTTP_409_CONFLICT,
            )
        resume = build_resume_limites(eid, request)
        return Response(ResumeLimitesSerializer(resume).data)


class DemanderAbonnementView(APIView):
    """Demande d'abonnement payant (activation manuelle en attendant le paiement en ligne)."""
    permission_classes = [IsAuthenticated, AEntrepriseContexte]

    @swagger_auto_schema(request_body=DemandeAbonnementSerializer, responses={201: AbonnementEntrepriseSerializer()})
    def post(self, request):
        serializer = DemandeAbonnementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        from stock.models import Entreprise
        entreprise = Entreprise.objects.filter(id=eid).first()
        if not entreprise:
            return Response({'detail': _('Entreprise introuvable.')}, status=status.HTTP_400_BAD_REQUEST)
        try:
            abonnement = demander_abonnement(
                entreprise,
                serializer.validated_data['formule_code'],
                serializer.validated_data['periode'],
                user=request.user,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            AbonnementEntrepriseSerializer(abonnement).data,
            status=status.HTTP_201_CREATED,
        )


class InfoInstallationPriveeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'message': MESSAGE_INSTALLATION_PRIVEE})


class DemandeInstallationPriveeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=DemandeInstallationPriveeSerializer, responses={201: DemandeInstallationPriveeSerializer()})
    def post(self, request):
        serializer = DemandeInstallationPriveeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        obj = DemandeInstallationPrivee.objects.create(
            entreprise_id=eid,
            utilisateur=request.user,
            **serializer.validated_data,
        )
        return Response(DemandeInstallationPriveeSerializer(obj).data, status=status.HTTP_201_CREATED)


class PlateformeAbonnementViewSet(viewsets.ReadOnlyModelViewSet):
    """Administration plateforme : abonnements de toutes les entreprises."""
    serializer_class = PlateformeAbonnementSerializer
    permission_classes = [EstSuperAdminPlateforme]

    def get_queryset(self):
        qs = AbonnementEntreprise.objects.select_related(
            'formule', 'entreprise',
        ).order_by('-created_at')
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        if self.request.query_params.get('en_attente') == '1':
            qs = qs.filter(statut=AbonnementEntreprise.STATUT_EN_ATTENTE)
        entreprise_id = self.request.query_params.get('entreprise_id')
        if entreprise_id:
            qs = qs.filter(entreprise_id=entreprise_id)
        return qs

    @swagger_auto_schema(
        responses={200: openapi.Response('Statistiques globales SuperAdmin')},
    )
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """KPIs globaux superadmin (entreprises, licences, demandes, revenus estimés)."""
        from stock.models import Entreprise

        entreprises_total = Entreprise.objects.count()
        entreprises_avec_abonnement = AbonnementEntreprise.objects.values('entreprise_id').distinct().count()
        entreprises_sans_abonnement = max(0, entreprises_total - entreprises_avec_abonnement)

        courants = AbonnementEntreprise.objects.filter(est_courant=True)
        repartition_statut = list(
            courants.values('statut')
            .annotate(total=Count('id'))
            .order_by('statut')
        )
        repartition_plans = list(
            courants.values('formule__code', 'formule__nom')
            .annotate(total=Count('id'))
            .order_by('formule__code')
        )
        demandes_en_attente = courants.filter(statut=AbonnementEntreprise.STATUT_EN_ATTENTE).count()
        licences_actives = courants.filter(statut__in=[
            AbonnementEntreprise.STATUT_ACTIF,
            AbonnementEntreprise.STATUT_ESSAI,
        ]).count()
        licences_expirees = courants.filter(statut=AbonnementEntreprise.STATUT_EXPIRE).count()
        licences_suspendues = courants.filter(statut=AbonnementEntreprise.STATUT_SUSPENDU).count()

        revenus_estimes = (
            courants.filter(statut__in=[AbonnementEntreprise.STATUT_ACTIF, AbonnementEntreprise.STATUT_ESSAI])
            .aggregate(total=Sum('formule__prix_mensuel'))
            .get('total')
            or 0
        )

        return Response({
            'entreprises': {
                'total': entreprises_total,
                'avec_abonnement_courant': entreprises_avec_abonnement,
                'sans_abonnement_courant': entreprises_sans_abonnement,
            },
            'licences': {
                'actives': licences_actives,
                'expirees': licences_expirees,
                'suspendues': licences_suspendues,
                'demandes_en_attente': demandes_en_attente,
                'repartition_statut': repartition_statut,
            },
            'plans': {
                'repartition': repartition_plans,
                'revenu_mensuel_estime': str(revenus_estimes),
            },
        })

    @swagger_auto_schema(responses={200: PlateformeAbonnementSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='en-attente')
    def en_attente(self, request):
        """File d'attente des activations manuelles (superadmin)."""
        qs = self.get_queryset().filter(statut=AbonnementEntreprise.STATUT_EN_ATTENTE)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=ActivationManuelleParEntrepriseSerializer,
        responses={200: PlateformeAbonnementSerializer()},
    )
    @action(detail=False, methods=['post'], url_path='activer-par-entreprise')
    def activer_par_entreprise(self, request):
        """Active la licence en attente d'une entreprise (après vérification paiement)."""
        ser = ActivationManuelleParEntrepriseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            abonnement = activer_abonnement_pour_entreprise(
                ser.validated_data['entreprise_id'],
                request.user,
                notes=ser.validated_data.get('notes', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        abonnement = AbonnementEntreprise.objects.select_related(
            'formule', 'entreprise',
        ).get(pk=abonnement.pk)
        return Response(PlateformeAbonnementSerializer(abonnement).data)

    @swagger_auto_schema(request_body=ActivationManuelleSerializer, responses={200: AbonnementEntrepriseSerializer()})
    @action(detail=True, methods=['post'], url_path='activer')
    def activer(self, request, pk=None):
        abonnement = self.get_object()
        ser = ActivationManuelleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            abonnement = activer_abonnement_manuellement(
                abonnement,
                request.user,
                notes=ser.validated_data.get('notes', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AbonnementEntrepriseSerializer(abonnement).data)


class PlateformeJournalViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JournalActivationLicenceSerializer
    permission_classes = [EstSuperAdminPlateforme]

    def get_queryset(self):
        qs = JournalActivationLicence.objects.select_related('effectue_par').order_by('-created_at')
        entreprise_id = self.request.query_params.get('entreprise_id')
        if entreprise_id:
            qs = qs.filter(entreprise_id=entreprise_id)
        return qs
