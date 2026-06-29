"""Vues API paiement en ligne et webhooks."""
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from abonnements.models import PaiementAbonnement
from abonnements.permissions import AEntrepriseContexte, EstSuperAdminPlateforme
from abonnements.paiements import fournisseurs_disponibles
from abonnements.serializers import (
    InitierPaiementSerializer,
    StatutPaiementSerializer,
    WebhookSimulerSerializer,
)
from abonnements.services.paiement import (
    ErreurPaiement,
    get_statut_paiement,
    initier_paiement_en_ligne,
    traiter_webhook_paiement,
)


class FournisseursPaiementView(APIView):
    """Liste des moyens de paiement disponibles (public)."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'fournisseurs': fournisseurs_disponibles()})


class InitierPaiementView(APIView):
    """
    Démarre un paiement en ligne.
    Retourne url_paiement / reference — n'active pas la licence tant que le webhook n'est pas confirmé.
    """
    permission_classes = [IsAuthenticated, AEntrepriseContexte]

    @swagger_auto_schema(request_body=InitierPaiementSerializer)
    def post(self, request):
        ser = InitierPaiementSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        from stock.models import Entreprise
        entreprise = Entreprise.objects.filter(id=eid).first()
        if not entreprise:
            return Response({'detail': _('Entreprise introuvable.')}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = initier_paiement_en_ligne(
                entreprise,
                ser.validated_data['formule_code'],
                ser.validated_data['periode'],
                ser.validated_data['fournisseur'],
                user=request.user,
            )
        except ErreurPaiement as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


class StatutPaiementView(APIView):
    """Consulte le statut d'un paiement par reference_interne."""
    permission_classes = [IsAuthenticated, AEntrepriseContexte]

    @swagger_auto_schema(responses={200: StatutPaiementSerializer()})
    def get(self, request, reference_interne):
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        data = get_statut_paiement(reference_interne, entreprise_id=eid)
        if not data:
            return Response({'detail': _('Paiement introuvable.')}, status=status.HTTP_404_NOT_FOUND)
        return Response(StatutPaiementSerializer(data).data)


class WebhookPaiementBaseView(APIView):
    """Base webhook — signature vérifiée avant traitement."""
    permission_classes = [AllowAny]
    fournisseur_code: str = ''

    def post(self, request, *args, **kwargs):
        from abonnements.paiements import get_gateway

        gateway = get_gateway(self.fournisseur_code)
        if not gateway.verifier_signature_webhook(request):
            return Response(
                {'detail': _('Signature webhook invalide.')},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            result = traiter_webhook_paiement(
                self.fournisseur_code,
                request.data if isinstance(request.data, dict) else {},
                ip_source=request.META.get('REMOTE_ADDR'),
            )
        except ErreurPaiement as exc:
            code_http = status.HTTP_400_BAD_REQUEST
            if exc.code == 'paiement_introuvable':
                code_http = status.HTTP_404_NOT_FOUND
            return Response({'detail': str(exc), 'code': exc.code}, status=code_http)
        return Response(result, status=status.HTTP_200_OK)


class WebhookMaishaPayView(WebhookPaiementBaseView):
    fournisseur_code = 'maisha_pay'


class WebhookFlexPayView(WebhookPaiementBaseView):
    fournisseur_code = 'flexpay'


class WebhookSerdinatePayView(WebhookPaiementBaseView):
    fournisseur_code = 'serdinate_pay'


class SimulerWebhookPaiementView(APIView):
    """
    Sandbox dev : simule une confirmation gateway (superadmin ou sandbox mode).
    En production désactivé si PAIEMENT_GATEWAY_SANDBOX=False.
    """
    permission_classes = [EstSuperAdminPlateforme]

    @swagger_auto_schema(request_body=WebhookSimulerSerializer)
    def post(self, request):
        from django.conf import settings
        if not getattr(settings, 'PAIEMENT_GATEWAY_SANDBOX', False):
            return Response(
                {'detail': _('Simulation désactivée en production.')},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = WebhookSimulerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ref = ser.validated_data['reference_interne']
        fournisseur = ser.validated_data['fournisseur']
        paiement = PaiementAbonnement.objects.filter(reference_interne=ref).first()
        if not paiement:
            return Response({'detail': _('Paiement introuvable.')}, status=status.HTTP_404_NOT_FOUND)
        payload = {
            'reference_interne': ref,
            'reference_externe': f'SIM-{ref[:8]}',
            'status': 'success',
            'amount': str(paiement.montant),
            'currency': paiement.devise,
        }
        try:
            result = traiter_webhook_paiement(
                fournisseur,
                payload,
                ip_source=request.META.get('REMOTE_ADDR'),
            )
        except ErreurPaiement as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)
