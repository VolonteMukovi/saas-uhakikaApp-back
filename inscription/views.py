from django.utils.translation import gettext as _

from drf_yasg.utils import swagger_auto_schema

from rest_framework import status

from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework.response import Response

from rest_framework.views import APIView



from abonnements.services.licence import build_etat_licence

from inscription.serializers import (

    ConnexionGoogleSerializer,

    GoogleConfigSerializer,

    InscriptionCompteSerializer,

    StatutOnboardingSerializer,

)

from inscription.services.email_responses import build_reponse_attente_verification
from inscription.services.email_messaging import envoyer_email_verification
from inscription.services.auth_response import build_jwt_login_response

from inscription.services.bootstrap_saas import assurer_contexte_initial_utilisateur

from inscription.services.google_oauth import (

    ErreurConnexionGoogle,

    connecter_ou_inscrire_via_google,

    verifier_id_token_google,

    _client_ids_autorises,

)





def _build_statut_onboarding(user, request=None):

    eid = getattr(request, 'tenant_id', None) if request else None

    if not eid:

        eid = user.get_entreprise_id(request)

    ent = user.get_entreprise(request) if eid else None

    a_entreprise = ent is not None



    if not a_entreprise:

        prochaine_etape = 'creer_entreprise'

        etat_licence = None

    else:

        etat_licence = build_etat_licence(ent.id)

        if etat_licence.get('est_actif'):

            prochaine_etape = 'utiliser_application'

        elif etat_licence.get('statut') == 'en_attente':

            prochaine_etape = 'attendre_validation_abonnement'

        elif etat_licence.get('statut') == 'expire':

            prochaine_etape = 'choisir_formule_payante'

        else:

            prochaine_etape = 'choisir_formule_payante'



    return {

        'utilisateur_id': user.id,

        'username': user.username,

        'email': user.email or '',

        'email_verifie': bool(getattr(user, 'email_verifie', False)),

        'a_entreprise': a_entreprise,

        'entreprise_id': ent.id if ent else None,

        'entreprise_nom': ent.nom if ent else None,

        'prochaine_etape': prochaine_etape,

        'etat_licence': etat_licence,

    }





def _reponse_auth_inscription(user, request, est_nouveau_compte=False, message=None):

    if not getattr(user, 'email_verifie', False):
        envoyer_email_verification(user, forcer=not est_nouveau_compte)
        body = build_reponse_attente_verification(
            user,
            connexion_google=True,
            est_nouveau_compte=est_nouveau_compte,
        )
        body['message'] = message or body['message']
        return body

    tokens_payload = build_jwt_login_response(user, request)
    bootstrap = tokens_payload.pop('bootstrap', None)

    statut = _build_statut_onboarding(user, request)

    body = {
        **StatutOnboardingSerializer(statut).data,
        'est_nouveau_compte': est_nouveau_compte,
        'connexion_google': True,
        'tokens': {
            'refresh': tokens_payload['refresh'],
            'access': tokens_payload['access'],
        },
        'user': tokens_payload['user'],
        'message': message or '',
    }
    if bootstrap:
        body['bootstrap'] = bootstrap
    return body





class InscriptionCompteView(APIView):

    """

    Inscription SaaS publique.

    Après inscription, l'utilisateur doit créer son entreprise (essai 2 mois automatique).

    """

    permission_classes = [AllowAny]



    @swagger_auto_schema(request_body=InscriptionCompteSerializer, responses={201: StatutOnboardingSerializer()})

    def post(self, request):

        serializer = InscriptionCompteSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        envoyer_email_verification(user, forcer=True)
        body = build_reponse_attente_verification(user, connexion_google=False, est_nouveau_compte=True)
        return Response(body, status=status.HTTP_201_CREATED)





class ConnexionGoogleView(APIView):

    """

    Connexion ou inscription via Google Identity Services.

    Le frontend envoie le jeton ID (`credential`) obtenu après « Continuer avec Google ».

    """

    permission_classes = [AllowAny]



    @swagger_auto_schema(request_body=ConnexionGoogleSerializer)

    def post(self, request):

        serializer = ConnexionGoogleSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        try:

            payload = verifier_id_token_google(serializer.validated_data['id_token'])

            user, est_nouveau = connecter_ou_inscrire_via_google(payload)

        except ErreurConnexionGoogle as exc:

            http_status = status.HTTP_503_SERVICE_UNAVAILABLE if exc.code == 'google_not_configured' else status.HTTP_400_BAD_REQUEST

            body = {'detail': str(exc), 'code': exc.code}
            if exc.hint:
                body['hint'] = exc.hint
            return Response(body, status=http_status)



        if est_nouveau:

            message = _(

                'Compte créé via Google. Un e-mail de confirmation vous a été envoyé.'

            )

            http_status = status.HTTP_201_CREATED

        else:

            message = _('Connexion Google réussie.')

            http_status = status.HTTP_200_OK

        body = _reponse_auth_inscription(user, request, est_nouveau_compte=est_nouveau, message=message)
        if not user.email_verifie:
            http_status = status.HTTP_201_CREATED if est_nouveau else status.HTTP_403_FORBIDDEN

        return Response(body, status=http_status)





class GoogleConfigView(APIView):

    """Configuration publique pour initialiser le bouton Google côté frontend."""

    permission_classes = [AllowAny]



    @swagger_auto_schema(responses={200: GoogleConfigSerializer()})

    def get(self, request):

        client_ids = _client_ids_autorises()

        data = {

            'client_ids': client_ids,

            'actif': bool(client_ids),

        }

        return Response(GoogleConfigSerializer(data).data)





class StatutOnboardingView(APIView):

    """État d'avancement onboarding : entreprise, essai, abonnement."""

    permission_classes = [IsAuthenticated]



    @swagger_auto_schema(responses={200: StatutOnboardingSerializer()})

    def get(self, request):

        assurer_contexte_initial_utilisateur(request.user)
        statut = _build_statut_onboarding(request.user, request)

        return Response(StatutOnboardingSerializer(statut).data)


