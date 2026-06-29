from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _


class InscriptionCompteSerializer(serializers.ModelSerializer):
    """Inscription publique d'un futur administrateur d'entreprise."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(_('Les mots de passe ne correspondent pas'))
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = get_user_model().objects.create_user(role='admin', **validated_data)
        user.set_password(password)
        user.save()
        return user


class StatutOnboardingSerializer(serializers.Serializer):
    utilisateur_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    a_entreprise = serializers.BooleanField()
    entreprise_id = serializers.IntegerField(allow_null=True)
    entreprise_nom = serializers.CharField(allow_null=True)
    prochaine_etape = serializers.CharField()
    etat_licence = serializers.DictField(required=False)


class ConnexionGoogleSerializer(serializers.Serializer):
    """
    Jeton ID renvoyé par Google Identity Services (GIS) côté frontend.
    Alias accepté : credential (réponse One Tap / bouton Google).
    """
    id_token = serializers.CharField(required=False, allow_blank=True)
    credential = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        token = (attrs.get('id_token') or attrs.get('credential') or '').strip()
        if not token:
            raise serializers.ValidationError(
                _('Le jeton Google (id_token ou credential) est obligatoire.')
            )

        sample = token[:300].lower()
        if (
            sample.startswith('<!doctype')
            or sample.startswith('<html')
            or '<head>' in sample
            or 'gis.provider' in sample
            or 'accounts.google.com' in sample
        ):
            raise serializers.ValidationError(
                _(
                    'Vous envoyez la page HTML du bouton Google, pas le jeton JWT. '
                    'Utilisez uniquement response.credential dans le callback GIS '
                    '(google.accounts.id.initialize → callback), pas le contenu de l\'iframe.'
                ),
                code='invalid_credential_source',
            )

        if token.count('.') != 2:
            raise serializers.ValidationError(
                _(
                    'Le credential doit être un JWT Google (forme xxx.yyy.zzz). '
                    'Récupérez-le via callback: (response) => response.credential après le clic Google.'
                ),
                code='invalid_token_format',
            )

        attrs['id_token'] = token
        return attrs


class GoogleConfigSerializer(serializers.Serializer):
    client_ids = serializers.ListField(child=serializers.CharField())
    actif = serializers.BooleanField()


class CreerEntrepriseMinimaleSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=255)
    pays = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    ville = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    email_entreprise = serializers.EmailField(required=False, allow_blank=True, default='')
    formule_code = serializers.CharField(required=False, default='essai_gratuit')
    periode = serializers.ChoiceField(
        choices=['essai', 'mensuel', 'annuel'],
        required=False,
        default='essai',
    )
    source_activation = serializers.ChoiceField(
        choices=['essai_gratuit', 'manuel', 'paiement_en_ligne'],
        required=False,
        default='essai_gratuit',
    )
    fournisseur_paiement = serializers.ChoiceField(
        choices=['maisha_pay', 'flexpay', 'serdinate_pay'],
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        if attrs.get('source_activation') == 'paiement_en_ligne' and not attrs.get('fournisseur_paiement'):
            raise serializers.ValidationError({
                'fournisseur_paiement': _('Obligatoire pour un paiement en ligne.'),
            })
        return attrs


class EtatFlowSaasSerializer(serializers.Serializer):
    authentifie = serializers.BooleanField()
    a_entreprise = serializers.BooleanField()
    entreprise_id = serializers.IntegerField(allow_null=True)
    entreprise_nom = serializers.CharField(allow_null=True)
    configuration_entreprise_complete = serializers.BooleanField()
    profil_complet = serializers.BooleanField()
    statut_flow = serializers.CharField()
    statut_licence_frontend = serializers.CharField(allow_null=True)
    acces_dashboard = serializers.BooleanField()
    operations_metier_autorisees = serializers.BooleanField()
    licence_active = serializers.BooleanField()
    activation_manuelle_en_attente = serializers.BooleanField()
    peut_completer_entreprise = serializers.BooleanField()
    peut_completer_profil = serializers.BooleanField()
    pages_onboarding_autorisees = serializers.ListField(child=serializers.CharField())
    bannieres = serializers.ListField(child=serializers.DictField())
    etat_licence = serializers.DictField(allow_null=True)
    limites_plan = serializers.DictField(allow_null=True)
    messages = serializers.ListField(child=serializers.CharField())
    actions_recommandees = serializers.ListField(child=serializers.DictField())
    regles_verification = serializers.DictField()
