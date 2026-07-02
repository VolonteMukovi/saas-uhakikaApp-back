from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers

from caisse.constants import CODE_TYPE_CAISSE_CHOICES
from caisse.models import DetailMouvementCaisse, MouvementCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse, mouvement_moyen_affiche
from caisse.services.caisse_defaut import CaisseError, caisse_necessite_session, parse_type_caisse_id_from_payload
from stock.models import DetteClient, Devise
from stock.serializers import DeviseSerializer
from stock.services.currency import assert_caisse_devise_compatible


class TypeCaisseSerializer(serializers.ModelSerializer):
    """CRUD caisses (canaux d'encaissement) par entreprise / succursale."""

    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(),
        source='devise',
        write_only=True,
        required=False,
        allow_null=True,
    )
    code_type_display = serializers.CharField(source='get_code_type_display', read_only=True)
    necessite_session = serializers.SerializerMethodField()
    requires_session = serializers.SerializerMethodField()

    class Meta:
        model = TypeCaisse
        fields = [
            'id', 'nom', 'libelle', 'code_type', 'code_type_display', 'description', 'image',
            'entreprise', 'succursale', 'devise', 'devise_id', 'is_active', 'est_defaut',
            'necessite_session', 'requires_session', 'created_at',
        ]
        read_only_fields = ['created_at', 'entreprise', 'est_defaut', 'necessite_session', 'requires_session']

    def get_necessite_session(self, obj):
        return caisse_necessite_session(obj)

    def get_requires_session(self, obj):
        return caisse_necessite_session(obj)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        req = self.context.get('request')
        if req and getattr(req.user, 'is_authenticated', False):
            eid = getattr(req, 'tenant_id', None) or (
                req.user.get_entreprise_id(req) if hasattr(req.user, 'get_entreprise_id') else None
            )
            if eid:
                self.fields['devise_id'].queryset = Devise.objects.filter(entreprise_id=eid)

    def validate_code_type(self, value):
        valid = {c[0] for c in CODE_TYPE_CAISSE_CHOICES}
        if value not in valid:
            raise serializers.ValidationError(_('Type de caisse invalide.'))
        return value

    def validate(self, attrs):
        if self.instance and self.instance.est_defaut:
            if attrs.get('is_active') is False:
                raise serializers.ValidationError(
                    {'is_active': _('La caisse principale par défaut ne peut pas être désactivée.')}
                )
        return attrs


class DetailMouvementCaisseSerializer(serializers.ModelSerializer):
    type_caisse = TypeCaisseSerializer(read_only=True)
    type_caisse_id = serializers.PrimaryKeyRelatedField(
        queryset=TypeCaisse.objects.all(), source='type_caisse', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = DetailMouvementCaisse
        fields = ['id', 'type_caisse', 'type_caisse_id', 'montant', 'motif_explicite', 'reference_piece']


class MouvementCaisseSerializer(serializers.ModelSerializer):
    """
    Mouvement de caisse : montant, devise, type, motif, moyen, caisse obligatoire.
    """
    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(),
        source='devise',
        write_only=True,
        required=False,
        allow_null=False,
    )
    type_caisse_detail = TypeCaisseSerializer(source='type_caisse', read_only=True)
    type_caisse_id = serializers.PrimaryKeyRelatedField(
        queryset=TypeCaisse.objects.filter(is_active=True),
        source='type_caisse',
        write_only=True,
        required=True,
    )
    details = DetailMouvementCaisseSerializer(many=True, read_only=True)
    resume = serializers.SerializerMethodField(read_only=True)
    content_type_modele = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MouvementCaisse
        fields = [
            'id', 'date', 'montant', 'devise', 'devise_id', 'devise_reference', 'taux_change', 'montant_reference',
            'type', 'motif', 'moyen', 'resume',
            'content_type_modele', 'object_id', 'utilisateur', 'reference_piece', 'sortie', 'entree',
            'session_caisse', 'type_caisse', 'type_caisse_id', 'type_caisse_detail', 'categorie', 'details',
        ]
        read_only_fields = [
            'id', 'date', 'devise_reference', 'taux_change', 'montant_reference',
            'object_id', 'utilisateur', 'session_caisse', 'type_caisse', 'categorie',
        ]

    def get_resume(self, obj):
        return obj.motif_affiche()

    def get_content_type_modele(self, obj):
        return obj.content_type.model if obj.content_type_id else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        req = self.context.get('request')
        if req and getattr(req.user, 'is_authenticated', False):
            eid = getattr(req, 'tenant_id', None) or (
                req.user.get_entreprise_id(req) if hasattr(req.user, 'get_entreprise_id') else None
            )
            if eid:
                self.fields['devise_id'].queryset = Devise.objects.filter(entreprise_id=eid)
                self.fields['type_caisse_id'].queryset = TypeCaisse.objects.filter(
                    entreprise_id=eid, is_active=True,
                )

    def validate(self, attrs):
        m = attrs.get('montant')
        if m is not None and m < 0:
            raise serializers.ValidationError(_('Le montant ne peut pas être négatif.'))
        if not attrs.get('devise') and not self.instance:
            raise serializers.ValidationError(_('Le champ devise est obligatoire pour le mouvement de caisse.'))
        tc = attrs.get('type_caisse')
        if not self.instance and not tc:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Veuillez sélectionner une caisse avant de valider cette opération.')}
            )
        if tc and not tc.is_active:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Cette opération financière exige une caisse active.')}
            )
        return attrs

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if 'devise' in data and 'devise_id' not in data:
            data['devise_id'] = data.pop('devise')
        if 'caisse' in data and 'type_caisse_id' not in data:
            data['type_caisse_id'] = data.pop('caisse')
        if 'caisse_id' in data and 'type_caisse_id' not in data:
            data['type_caisse_id'] = data.pop('caisse_id')
        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):
        tenant_id = validated_data.pop('entreprise_id', None)
        branch_id = validated_data.pop('succursale_id', None)
        devise = validated_data.pop('devise')
        type_caisse = validated_data.pop('type_caisse')
        type_m = validated_data.pop('type')
        montant = validated_data.pop('montant')
        motif = (validated_data.pop('motif', None) or '').strip()
        moyen = validated_data.pop('moyen', None)
        if moyen is not None:
            moyen = (moyen or '').strip() or None
        ref = (validated_data.pop('reference_piece', None) or '') or ''

        req = self.context.get('request')
        if tenant_id is None and req and req.user.is_authenticated and hasattr(req.user, 'get_entreprise_id'):
            tenant_id = getattr(req, 'tenant_id', None) or req.user.get_entreprise_id(req)
        if branch_id is None and req:
            branch_id = getattr(req, 'branch_id', None)
        user = req.user if req and req.user.is_authenticated else None

        return creer_mouvement_caisse(
            montant=montant,
            devise=devise,
            type_mouvement=type_m,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            content_object=None,
            utilisateur=user,
            reference_piece=ref,
            motif=motif,
            moyen=moyen,
            type_caisse=type_caisse,
        )


class PaiementDetteReadSerializer(serializers.Serializer):
    """Représente un MouvementCaisse lié à une DetteClient (entrée de caisse, compat. API historique)."""

    def to_representation(self, mc):
        dette = None
        if mc.content_type_id and mc.object_id:
            if ContentType.objects.get_for_model(DetteClient).id == mc.content_type_id:
                dette = DetteClient.objects.filter(pk=mc.object_id).select_related('client').first()
        moyen = mouvement_moyen_affiche(mc)
        dette_payload = None
        if dette:
            if self.context.get('include_dette_details', False):
                dette_payload = {
                    'id': dette.id,
                    'client_nom': dette.client.nom if dette.client else None,
                    'montant_total': str(dette.montant_total),
                    'solde_restant': str(dette.solde_restant),
                    'statut': dette.statut,
                }
            else:
                dette_payload = {
                    'id': dette.id,
                    'client_nom': dette.client.nom if dette.client else None,
                }
        caisse_payload = None
        if mc.type_caisse_id:
            caisse_payload = {
                'id': mc.type_caisse_id,
                'nom': mc.type_caisse.nom,
                'libelle': mc.type_caisse.libelle_affiche,
                'code_type': mc.type_caisse.code_type,
            }
        return {
            'id': mc.id,
            'dette': dette_payload,
            'montant_paye': str(mc.montant),
            'date_paiement': mc.date.isoformat() if mc.date else None,
            'moyen': moyen,
            'reference': mc.reference_piece or '',
            'utilisateur': mc.utilisateur_id,
            'devise': DeviseSerializer(mc.devise).data if mc.devise else None,
            'mouvement_caisse_id': mc.id,
            'type_caisse': caisse_payload,
            'session_caisse': mc.session_caisse_id,
        }


class PaiementDetteWriteSerializer(serializers.Serializer):
    dette_id = serializers.PrimaryKeyRelatedField(queryset=DetteClient.objects.all(), source='dette')
    montant_paye = serializers.DecimalField(max_digits=12, decimal_places=5)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(), source='devise', required=False, allow_null=True
    )
    taux_change = serializers.DecimalField(max_digits=20, decimal_places=8, required=False, allow_null=True)
    type_caisse_id = serializers.PrimaryKeyRelatedField(
        queryset=TypeCaisse.objects.filter(is_active=True),
        source='type_caisse',
        required=True,
    )
    moyen = serializers.CharField(required=False, allow_blank=True, default='')
    reference = serializers.CharField(required=False, allow_blank=True, default='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        req = self.context.get('request')
        if req and getattr(req.user, 'is_authenticated', False):
            eid = getattr(req, 'tenant_id', None) or (
                req.user.get_entreprise_id(req) if hasattr(req.user, 'get_entreprise_id') else None
            )
            if eid:
                self.fields['type_caisse_id'].queryset = TypeCaisse.objects.filter(
                    entreprise_id=eid, is_active=True,
                )
                self.fields['devise_id'].queryset = Devise.objects.filter(entreprise_id=eid)

    def validate(self, attrs):
        dette = attrs['dette']
        if dette.statut == 'PAYEE':
            raise serializers.ValidationError({'dette': _('Cette dette est déjà entièrement payée.')})
        montant = attrs['montant_paye']
        if montant > dette.solde_restant:
            raise serializers.ValidationError(
                {
                    'montant_paye': _(
                        'Le montant (%(m)s) dépasse le solde restant (%(s)s).'
                    )
                    % {'m': montant, 's': dette.solde_restant}
                }
            )
        if montant <= 0:
            raise serializers.ValidationError({'montant_paye': _('Le montant doit être positif.')})
        tc = attrs.get('type_caisse')
        if not tc:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Veuillez sélectionner une caisse avant de valider cette opération.')}
            )
        if not tc.is_active:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Cette opération financière exige une caisse active.')}
            )
        devise = attrs.get('devise') or dette.devise
        if devise:
            assert_caisse_devise_compatible(tc, devise)
        return attrs

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if 'caisse' in data and 'type_caisse_id' not in data:
            data['type_caisse_id'] = data.pop('caisse')
        if 'caisse_id' in data and 'type_caisse_id' not in data:
            data['type_caisse_id'] = data.pop('caisse_id')
        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):
        dette = validated_data['dette']
        montant = validated_data['montant_paye']
        devise = validated_data.get('devise') or dette.devise
        explicit_rate = validated_data.get('taux_change')
        type_caisse = validated_data['type_caisse']
        moyen = validated_data.get('moyen') or ''
        reference = validated_data.get('reference') or ''
        req = self.context.get('request')
        tenant_id = getattr(req, 'tenant_id', None) if req else None
        branch_id = getattr(req, 'branch_id', None) if req else None
        if not tenant_id and req and req.user.is_authenticated and hasattr(req.user, 'get_entreprise_id'):
            tenant_id = req.user.get_entreprise_id(req)
        user = req.user if req and req.user.is_authenticated else None
        if not devise:
            raise serializers.ValidationError({'devise_id': _('Devise requise (dette sans devise).')})

        motif = moyen.strip() or (
            f"Paiement dette — {dette.client.nom if dette.client else ''} — {montant}"
        )

        return creer_mouvement_caisse(
            montant=montant,
            devise=devise,
            type_mouvement='ENTREE',
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            content_object=dette,
            utilisateur=user,
            reference_piece=reference,
            motif=motif,
            moyen=moyen.strip() or None,
            type_caisse=type_caisse,
            taux_change=explicit_rate,
        )


PaiementDetteSerializer = PaiementDetteReadSerializer
