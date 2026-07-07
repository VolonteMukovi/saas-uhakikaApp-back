"""Endpoints parcours onboarding (statut, profil, entreprise, finalisation, bienvenue)."""
from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inscription.services.auth_response import build_jwt_login_response
from inscription.services.onboarding_actions import (
    ErreurOnboarding,
    finaliser_onboarding,
    marquer_welcome_vu,
    mettre_a_jour_entreprise_onboarding,
    mettre_a_jour_profil_onboarding,
    renvoyer_email_activation,
)
from inscription.services.onboarding_status import build_onboarding_status
from inscription.services.workspace_activation import (
    ErreurActivationEspace,
    activer_espace_avec_jeton,
    build_frontend_welcome_url,
)


class OnboardingProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)


class OnboardingCompanySerializer(serializers.Serializer):
    nom = serializers.CharField(required=False, allow_blank=True)
    secteur = serializers.CharField(required=False, allow_blank=True)
    pays = serializers.CharField(required=False, allow_blank=True)
    ville = serializers.CharField(required=False, allow_blank=True)
    adresse = serializers.CharField(required=False, allow_blank=True)
    telephone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    responsable = serializers.CharField(required=False, allow_blank=True)
    nif = serializers.CharField(required=False, allow_blank=True)
    slogan = serializers.CharField(required=False, allow_blank=True)


class WorkspaceActivationSerializer(serializers.Serializer):
    token = serializers.CharField()


def _erreur_onboarding_response(exc: ErreurOnboarding, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({'title': exc.title, 'detail': str(exc.detail)}, status=http_status)


def _erreur_activation_response(exc: ErreurActivationEspace, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({'title': exc.title, 'detail': str(exc.detail)}, status=http_status)


class OnboardingStatusView(APIView):
    """GET /api/onboarding/status/ — état précis + next_step."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_onboarding_status(request.user, request))


class OnboardingProfileView(APIView):
    """PATCH /api/onboarding/profile/ — complétion profil (étape 1)."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=OnboardingProfileSerializer)
    def patch(self, request):
        serializer = OnboardingProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            data = mettre_a_jour_profil_onboarding(request.user, serializer.validated_data)
        except ErreurOnboarding as exc:
            return _erreur_onboarding_response(exc)
        return Response(data)


class OnboardingCompanyView(APIView):
    """PATCH /api/onboarding/company/ — complétion entreprise (étape 2)."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=OnboardingCompanySerializer)
    def patch(self, request):
        serializer = OnboardingCompanySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            data = mettre_a_jour_entreprise_onboarding(
                request.user, serializer.validated_data, request,
            )
        except ErreurOnboarding as exc:
            return _erreur_onboarding_response(exc)
        return Response(data)


class OnboardingCompleteView(APIView):
    """POST /api/onboarding/complete/ — finalise onboarding + envoi e-mail activation."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = finaliser_onboarding(request.user, request)
        except ErreurOnboarding as exc:
            return _erreur_onboarding_response(exc)
        return Response(data)


class OnboardingMarkWelcomeSeenView(APIView):
    """POST /api/onboarding/mark-welcome-seen/ — marque welcome_seen=true."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not getattr(request.user, 'workspace_activated', False):
            return Response(
                {
                    'title': _('Activation requise'),
                    'detail': _('Activez votre espace via le lien reçu par e-mail avant de continuer.'),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        data = marquer_welcome_vu(request.user, request)
        return Response(data)


class OnboardingActivateWorkspaceView(APIView):
    """POST /api/onboarding/activate-workspace/ — valide le jeton e-mail final."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=WorkspaceActivationSerializer)
    def post(self, request):
        serializer = WorkspaceActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, code = activer_espace_avec_jeton(serializer.validated_data['token'])
        except ErreurActivationEspace as exc:
            return _erreur_activation_response(exc)

        tokens_payload = build_jwt_login_response(user, request)
        statut = build_onboarding_status(user, request)
        body = {
            'success': True,
            'code': code,
            'message': _('Votre espace UHAKIKAAPP est activé. Bienvenue !'),
            'redirection': statut['redirection'],
            'onboarding': statut,
            'tokens': {
                'refresh': tokens_payload['refresh'],
                'access': tokens_payload['access'],
            },
            'user': tokens_payload['user'],
        }
        return Response(body)


class ActiverEspaceRedirectView(APIView):
    """
    GET depuis le lien e-mail d'activation finale.
    Redirige vers /fr/welcome?token=...
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = (request.GET.get('token') or '').strip()
        if not token:
            path = getattr(settings, 'FRONTEND_WELCOME_PATH', '/welcome')
            from inscription.services.email_verification import build_frontend_url
            return HttpResponseRedirect(build_frontend_url(path))
        return HttpResponseRedirect(build_frontend_welcome_url(token))


class OnboardingResendActivationView(APIView):
    """POST /api/onboarding/resend-activation/ — renvoi e-mail activation finale."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = renvoyer_email_activation(request.user, request)
        except ErreurOnboarding as exc:
            return _erreur_onboarding_response(exc)
        http_status = status.HTTP_200_OK if data.get('email_envoye') else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(data, status=http_status)
