from rest_framework import serializers

from abonnements.models import (
    AbonnementEntreprise,
    DemandeInstallationPrivee,
    FormuleAbonnement,
    JournalActivationLicence,
    PaiementAbonnement,
)


class FormuleAbonnementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormuleAbonnement
        fields = [
            'id', 'code', 'nom', 'description',
            'prix_mensuel', 'prix_annuel', 'devise',
            'fonctionnalites', 'limites', 'ordre_affichage',
        ]


class PaiementAbonnementSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaiementAbonnement
        fields = [
            'id', 'montant', 'devise', 'statut', 'fournisseur',
            'reference_interne', 'reference_externe', 'url_paiement',
            'confirme_at', 'created_at',
        ]
        read_only_fields = fields


class AbonnementEntrepriseSerializer(serializers.ModelSerializer):
    formule = FormuleAbonnementSerializer(read_only=True)
    formule_code = serializers.SlugField(write_only=True, required=False)
    paiements = PaiementAbonnementSerializer(many=True, read_only=True)
    est_actif = serializers.BooleanField(read_only=True)
    jours_restants = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = AbonnementEntreprise
        fields = [
            'id', 'formule', 'formule_code', 'statut', 'periode',
            'date_debut', 'date_fin', 'renouvellement_auto',
            'activation_manuelle', 'est_courant', 'est_actif',
            'jours_restants', 'paiements', 'created_at',
        ]
        read_only_fields = [
            'id', 'formule', 'statut', 'date_debut', 'date_fin',
            'activation_manuelle', 'est_courant', 'created_at',
        ]


class PlateformeAbonnementSerializer(AbonnementEntrepriseSerializer):
    """Liste superadmin : contexte entreprise + contact admin."""
    entreprise_id = serializers.IntegerField(source='entreprise.id', read_only=True)
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)
    entreprise_email = serializers.EmailField(source='entreprise.email', read_only=True)
    admin_username = serializers.SerializerMethodField()
    admin_email = serializers.SerializerMethodField()

    class Meta(AbonnementEntrepriseSerializer.Meta):
        fields = AbonnementEntrepriseSerializer.Meta.fields + [
            'entreprise_id',
            'entreprise_nom',
            'entreprise_email',
            'admin_username',
            'admin_email',
            'notes',
        ]
        read_only_fields = list(AbonnementEntrepriseSerializer.Meta.read_only_fields) + [
            'entreprise_id',
            'entreprise_nom',
            'entreprise_email',
            'admin_username',
            'admin_email',
        ]

    def get_admin_username(self, obj):
        m = (
            obj.entreprise.memberships.filter(role='admin', is_active=True)
            .select_related('user')
            .order_by('id')
            .first()
        )
        return m.user.username if m else None

    def get_admin_email(self, obj):
        m = (
            obj.entreprise.memberships.filter(role='admin', is_active=True)
            .select_related('user')
            .order_by('id')
            .first()
        )
        return m.user.email if m else None


class DemandeAbonnementSerializer(serializers.Serializer):
    formule_code = serializers.SlugField()
    periode = serializers.ChoiceField(
        choices=[
            AbonnementEntreprise.PERIODE_MENSUEL,
            AbonnementEntreprise.PERIODE_ANNUEL,
        ],
    )


class EtatLicenceSerializer(serializers.Serializer):
    a_licence = serializers.BooleanField()
    abonnement_id = serializers.IntegerField(required=False, allow_null=True)
    statut = serializers.CharField()
    est_actif = serializers.BooleanField()
    est_essai = serializers.BooleanField()
    formule_code = serializers.CharField(allow_null=True)
    formule_nom = serializers.CharField(allow_null=True)
    periode = serializers.CharField(required=False, allow_null=True)
    date_debut = serializers.DateTimeField(required=False, allow_null=True)
    date_fin = serializers.DateTimeField(required=False, allow_null=True)
    jours_restants = serializers.IntegerField(required=False, allow_null=True)
    fonctionnalites = serializers.DictField()
    limites = serializers.DictField()
    activation_manuelle = serializers.BooleanField(required=False)
    message = serializers.CharField(allow_blank=True)


class DemandeInstallationPriveeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeInstallationPrivee
        fields = [
            'id', 'nom_contact', 'email_contact', 'telephone',
            'message', 'statut', 'created_at',
        ]
        read_only_fields = ['id', 'statut', 'created_at']


class JournalActivationLicenceSerializer(serializers.ModelSerializer):
    effectue_par_username = serializers.CharField(
        source='effectue_par.username', read_only=True, default=None,
    )

    class Meta:
        model = JournalActivationLicence
        fields = [
            'id', 'action', 'effectue_par_username', 'details', 'created_at',
        ]


class ActivationManuelleSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ActivationManuelleParEntrepriseSerializer(serializers.Serializer):
    entreprise_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ResumeLimitesSerializer(serializers.Serializer):
    formule_code = serializers.CharField(allow_null=True)
    formule_nom = serializers.CharField(allow_null=True)
    est_essai = serializers.BooleanField()
    fonctionnalites = serializers.DictField()
    utilisateurs = serializers.DictField()
    succursales = serializers.DictField()


class InitierPaiementSerializer(serializers.Serializer):
    formule_code = serializers.SlugField()
    periode = serializers.ChoiceField(
        choices=[
            'mensuel',
            'annuel',
        ],
    )
    fournisseur = serializers.ChoiceField(
        choices=[
            PaiementAbonnement.FOURNISSEUR_MAISHAPAY,
            PaiementAbonnement.FOURNISSEUR_FLEXPAY,
            PaiementAbonnement.FOURNISSEUR_SERDI,
        ],
    )


class StatutPaiementSerializer(serializers.Serializer):
    paiement_id = serializers.IntegerField()
    reference_interne = serializers.CharField()
    reference_externe = serializers.CharField(allow_blank=True)
    statut = serializers.CharField()
    montant = serializers.CharField()
    devise = serializers.CharField()
    fournisseur = serializers.CharField()
    url_paiement = serializers.URLField(allow_blank=True, required=False)
    confirme_at = serializers.DateTimeField(allow_null=True, required=False)
    abonnement = serializers.DictField()


class WebhookSimulerSerializer(serializers.Serializer):
    reference_interne = serializers.CharField()
    fournisseur = serializers.ChoiceField(
        choices=['maisha_pay', 'flexpay', 'serdinate_pay'],
    )
