"""Endpoints vérification d'e-mail."""
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from inscription.services.auth_response import build_jwt_login_response
from inscription.services.email_messaging import envoyer_email_verification
from inscription.services.email_responses import build_reponse_attente_verification, build_reponse_email_verifie
from inscription.services.email_verification import (
    ErreurVerificationEmail,
    confirmer_email_avec_jeton,
    modifier_email_en_attente,
)
from inscription.views import _build_statut_onboarding
from inscription.serializers import StatutOnboardingSerializer

User = get_user_model()


class VerifierEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class RenvoyerVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ModifierEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nouvel_email = serializers.EmailField()
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)


class VerifierEmailView(APIView):
    """Confirme l'adresse e-mail et ouvre une session JWT."""
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=VerifierEmailSerializer)
    def post(self, request):
        serializer = VerifierEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, code = confirmer_email_avec_jeton(serializer.validated_data['token'])
        except ErreurVerificationEmail as exc:
            return Response({'detail': str(exc.detail), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)

        if code == 'deja_verifie':
            tokens_payload = build_jwt_login_response(user, request)
            body = build_reponse_email_verifie(user, tokens_payload)
            body['code'] = 'deja_verifie'
            body['message'] = _('Votre adresse e-mail a déjà été confirmée. Vous pouvez vous connecter.')
            statut = _build_statut_onboarding(user, request)
            body['onboarding'] = StatutOnboardingSerializer(statut).data
            return Response(body, status=status.HTTP_200_OK)

        tokens_payload = build_jwt_login_response(user, request)
        body = build_reponse_email_verifie(user, tokens_payload)
        statut = _build_statut_onboarding(user, request)
        body['onboarding'] = StatutOnboardingSerializer(statut).data
        return Response(body, status=status.HTTP_200_OK)


class RenvoyerVerificationView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=RenvoyerVerificationSerializer)
    def post(self, request):
        serializer = RenvoyerVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()
        user = User.objects.filter(email__iexact=email, email_verifie=False).first()

        message_ok = _(
            'Si un compte en attente existe pour cette adresse, un nouveau message de confirmation vient d\'être envoyé.'
        )
        if not user:
            return Response({'message': message_ok, 'email_envoye': False})

        result = envoyer_email_verification(user)
        if result.get('code') == 'cooldown':
            return Response(
                {
                    'message': _('Veuillez patienter avant de demander un nouveau message.'),
                    'delai_renvoi_secondes': result.get('delai_renvoi_secondes', 0),
                    'code': 'cooldown',
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if result.get('code') == 'quota_depasse':
            return Response(
                {'message': _('Nombre maximum de demandes atteint. Réessayez plus tard.'), 'code': 'quota_depasse'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        return Response({
            'message': _('Un nouveau message de confirmation vient d\'être envoyé.'),
            'email_envoye': bool(result.get('envoye')),
            'delai_renvoi_secondes': result.get('delai_renvoi_secondes', 60),
        })


class ModifierEmailVerificationView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=ModifierEmailVerificationSerializer)
    def post(self, request):
        serializer = ModifierEmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip().lower()
        user = User.objects.filter(email__iexact=email, email_verifie=False).first()
        if not user:
            return Response(
                {'detail': _('Aucun compte en attente trouvé pour cette adresse.'), 'code': 'compte_introuvable'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            modifier_email_en_attente(
                user,
                serializer.validated_data['nouvel_email'],
                password=serializer.validated_data.get('password') or None,
            )
        except ErreurVerificationEmail as exc:
            return Response({'detail': str(exc.detail), 'code': exc.code}, status=400)

        from inscription.services.email_messaging import envoyer_email_verification
        envoyer_email_verification(user, forcer=True)
        user.refresh_from_db()
        return Response(build_reponse_attente_verification(user, est_nouveau_compte=False))
