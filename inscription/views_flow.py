"""Vues flow SaaS unifié (dashboard guard)."""
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inscription.serializers import (
    CreerEntrepriseMinimaleSerializer,
    EtatFlowSaasSerializer,
)
from inscription.services.auth_response import build_jwt_login_response
from inscription.services.entreprise_saas import creer_entreprise_minimale
from inscription.services.flow_saas import build_etat_flow_saas


class FlowSaasView(APIView):
    """
    État complet du flow SaaS pour le frontend.
    Utiliser pour DashboardAccessGuard, bannières et menus verrouillés.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: EtatFlowSaasSerializer()})
    def get(self, request):
        etat = build_etat_flow_saas(request.user, request)
        return Response(EtatFlowSaasSerializer(etat).data)


class CreerEntrepriseMinimaleView(APIView):
    """
    Étape 3 du flow : création minimale entreprise + licence selon plan choisi.
    Redirection dashboard immédiate possible après succès.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=CreerEntrepriseMinimaleSerializer)
    def post(self, request):
        ser = CreerEntrepriseMinimaleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            result = creer_entreprise_minimale(
                request.user,
                nom=data['nom'],
                pays=data.get('pays', ''),
                ville=data.get('ville', ''),
                email_entreprise=data.get('email_entreprise', ''),
                formule_code=data.get('formule_code', 'essai_gratuit'),
                periode=data.get('periode', 'essai'),
                source_activation=data.get('source_activation', 'essai_gratuit'),
                fournisseur_paiement=data.get('fournisseur_paiement'),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        tokens = build_jwt_login_response(request.user, request)
        flow = build_etat_flow_saas(request.user, request)

        return Response(
            {
                **result,
                **EtatFlowSaasSerializer(flow).data,
                'tokens': {
                    'refresh': tokens['refresh'],
                    'access': tokens['access'],
                },
                'user': tokens['user'],
                'redirection': '/dashboard',
            },
            status=status.HTTP_201_CREATED,
        )
