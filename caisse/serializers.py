from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from stock.tenant_fields import TenantPrimaryKeyRelatedField

from caisse.constants import CODE_TYPE_CAISSE_CHOICES
from caisse.models import DetailMouvementCaisse, MouvementCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse, mouvement_moyen_affiche
from caisse.services.caisse_defaut import CaisseError, caisse_necessite_session, parse_type_caisse_id_from_payload
from stock.models import Devise
from caisse.services.currency_conversion import prepare_caisse_movement
from stock.serializers import DeviseSerializer


class TypeCaisseSerializer(serializers.ModelSerializer):
    """CRUD caisses (canaux d'encaissement) par entreprise / succursale."""

    devise = DeviseSerializer(read_only=True)
    devise_id = TenantPrimaryKeyRelatedField(
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
    type_caisse_id = TenantPrimaryKeyRelatedField(
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
    devise_reference = DeviseSerializer(read_only=True)
    devise_id = TenantPrimaryKeyRelatedField(
        queryset=Devise.objects.all(),
        source='devise',
        write_only=True,
        required=False,
        allow_null=False,
    )
    taux_change = serializers.DecimalField(max_digits=20, decimal_places=8, required=False, allow_null=True)
    type_caisse_detail = TypeCaisseSerializer(source='type_caisse', read_only=True)
    type_caisse_id = TenantPrimaryKeyRelatedField(
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
            'montant_origine', 'devise_origine', 'taux_conversion', 'date_taux',
            'montant_applique', 'devise_applique',
            'type', 'motif', 'moyen', 'resume',
            'content_type_modele', 'object_id', 'utilisateur', 'reference_piece', 'sortie', 'entree',
            'session_caisse', 'type_caisse', 'type_caisse_id', 'type_caisse_detail', 'categorie', 'details',
        ]
        read_only_fields = [
            'id', 'date', 'devise_reference', 'taux_change', 'montant_reference',
            'montant_origine', 'devise_origine', 'taux_conversion', 'date_taux',
            'montant_applique', 'devise_applique',
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
            raise serializers.ValidationError(_('Le montant ne peut pas etre negatif.'))
        devise = attrs.get('devise') or (self.instance.devise if self.instance else None)
        if not devise and not self.instance:
            raise serializers.ValidationError(_('Le champ devise est obligatoire pour le mouvement de caisse.'))
        tc = attrs.get('type_caisse') or (self.instance.type_caisse if self.instance else None)
        if not self.instance and not tc:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Veuillez selectionner une caisse avant de valider cette operation.')}
            )
        if tc and not tc.is_active:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Cette operation financiere exige une caisse active.')}
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


class ConversionPreviewSerializer(serializers.Serializer):
    """Prévisualisation conversion opération → devise caisse (source de vérité backend)."""

    montant = serializers.DecimalField(max_digits=14, decimal_places=5)
    devise_id = TenantPrimaryKeyRelatedField(queryset=Devise.objects.all(), source='devise')
    type_caisse_id = TenantPrimaryKeyRelatedField(
        queryset=TypeCaisse.objects.filter(is_active=True),
        source='type_caisse',
    )
    date_operation = serializers.DateTimeField(required=False, allow_null=True)
    taux_change = serializers.DecimalField(max_digits=20, decimal_places=8, required=False, allow_null=True)

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
        montant = attrs['montant']
        if montant <= 0:
            raise serializers.ValidationError({'montant': _('Le montant doit être positif.')})
        tc = attrs['type_caisse']
        if not tc.is_active:
            raise serializers.ValidationError({'type_caisse_id': _('Caisse inactive.')})
        if not tc.devise_id:
            raise serializers.ValidationError({'type_caisse_id': _('La caisse n\'a pas de devise configurée.')})
        return attrs

    def build_preview(self) -> dict:
        attrs = self.validated_data
        req = self.context.get('request')
        tenant_id = getattr(req, 'tenant_id', None) if req else None
        if not tenant_id and req and getattr(req.user, 'is_authenticated', False):
            tenant_id = req.user.get_entreprise_id(req)
        try:
            conversion = prepare_caisse_movement(
                montant_operation=attrs['montant'],
                devise_operation=attrs['devise'],
                type_caisse=attrs['type_caisse'],
                entreprise_id=tenant_id,
                date_operation=attrs.get('date_operation'),
                explicit_conversion_rate=attrs.get('taux_change'),
            )
        except CaisseError as exc:
            raise serializers.ValidationError({'detail': str(exc)}) from exc
        payload = conversion.to_dict()
        payload['type_caisse'] = {
            'id': attrs['type_caisse'].pk,
            'nom': attrs['type_caisse'].nom,
            'libelle': attrs['type_caisse'].libelle_affiche,
        }
        return payload
