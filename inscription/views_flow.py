"""Vues flow SaaS unifié (dashboard guard)."""
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inscription.serializers import (
    BootstrapSaasSerializer,
    CreerEntrepriseMinimaleSerializer,
    EtatFlowSaasSerializer,
)
from inscription.services.auth_response import build_jwt_login_response
from inscription.services.bootstrap_saas import assurer_contexte_initial_utilisateur
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
        bootstrap = assurer_contexte_initial_utilisateur(request.user)
        etat = build_etat_flow_saas(request.user, request)
        data = dict(EtatFlowSaasSerializer(etat).data)
        if bootstrap.get('bootstrap_effectue'):
            tokens = build_jwt_login_response(request.user, request, bootstrap=False)
            data['bootstrap'] = bootstrap
            data['tokens'] = {
                'refresh': tokens['refresh'],
                'access': tokens['access'],
            }
            data['user'] = tokens['user']
        return Response(data)


class BootstrapSaasView(APIView):
    """
    Bootstrap explicite post-login : crée entreprise + essai si le contexte est incomplet.
    À appeler avant les endpoints métier si le frontend détecte un contexte vide.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=BootstrapSaasSerializer, responses={200: EtatFlowSaasSerializer()})
    def post(self, request):
        ser = BootstrapSaasSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        bootstrap = assurer_contexte_initial_utilisateur(
            request.user,
            nom_entreprise=data.get('nom') or None,
            pays=data.get('pays', ''),
        )
        flow = build_etat_flow_saas(request.user, request)
        tokens = build_jwt_login_response(request.user, request, bootstrap=False)
        return Response(
            {
                **EtatFlowSaasSerializer(flow).data,
                'bootstrap': bootstrap,
                'tokens': {
                    'refresh': tokens['refresh'],
                    'access': tokens['access'],
                },
                'user': tokens['user'],
                'message': bootstrap.get('message') or _('Contexte utilisateur prêt.'),
            },
            status=status.HTTP_200_OK,
        )


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

        tokens_payload = build_jwt_login_response(request.user, request, bootstrap=False)
        flow = build_etat_flow_saas(request.user, request)

        return Response(
            {
                **result,
                **EtatFlowSaasSerializer(flow).data,
                'tokens': {
                    'refresh': tokens_payload['refresh'],
                    'access': tokens_payload['access'],
                },
                'user': tokens_payload['user'],
                'redirection': '/dashboard',
            },
            status=status.HTTP_201_CREATED,
        )
