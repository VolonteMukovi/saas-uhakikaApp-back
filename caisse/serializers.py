from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from caisse.constants import CODE_TYPE_CAISSE_CHOICES
from caisse.models import DetailMouvementCaisse, MouvementCaisse, TypeCaisse
from caisse.services.caisse import creer_mouvement_caisse, mouvement_moyen_affiche
from caisse.services.caisse_defaut import CaisseError, caisse_necessite_session, parse_type_caisse_id_from_payload
from stock.models import Client, DetteClient, Devise
from caisse.services.currency_conversion import payment_equivalent_in_dette_currency, prepare_caisse_movement
from stock.serializers import DeviseSerializer


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
    devise_reference = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(),
        source='devise',
        write_only=True,
        required=False,
        allow_null=False,
    )
    taux_change = serializers.DecimalField(max_digits=20, decimal_places=8, required=False, allow_null=True)
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
            'montant_applique_dette': str(mc.montant_applique) if mc.montant_applique is not None else None,
            'montant_origine': str(mc.montant_origine) if mc.montant_origine is not None else None,
            'devise_origine': DeviseSerializer(mc.devise_origine).data if mc.devise_origine_id else None,
            'taux_conversion': str(mc.taux_conversion) if mc.taux_conversion is not None else None,
            'date_taux': mc.date_taux.isoformat() if mc.date_taux else None,
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
        tc = attrs.get('type_caisse')
        devise_paiement = attrs.get('devise') or dette.devise
        if not tc:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Veuillez sélectionner une caisse avant de valider cette opération.')}
            )
        if not tc.is_active:
            raise serializers.ValidationError(
                {'type_caisse_id': _('Cette opération financière exige une caisse active.')}
            )
        if not devise_paiement:
            raise serializers.ValidationError({'devise_id': _('Devise requise (dette sans devise).')})
        if montant <= 0:
            raise serializers.ValidationError({'montant_paye': _('Le montant doit être positif.')})

        dette_devise = dette.devise
        if not dette_devise:
            raise serializers.ValidationError({'dette': _('La dette n\'a pas de devise configurée.')})

        req = self.context.get('request')
        tenant_id = getattr(req, 'tenant_id', None) if req else None
        if not tenant_id and req and getattr(req.user, 'is_authenticated', False):
            tenant_id = req.user.get_entreprise_id(req)

        if devise_paiement.pk == dette_devise.pk:
            montant_applique_dette = montant
        else:
            try:
                montant_applique_dette, _ = payment_equivalent_in_dette_currency(
                    montant,
                    devise_paiement,
                    dette_devise,
                    entreprise_id=tenant_id,
                    explicit_rate=attrs.get('taux_change'),
                )
            except Exception as exc:
                raise serializers.ValidationError({'devise_id': str(exc)}) from exc

        if montant_applique_dette > dette.solde_restant:
            raise serializers.ValidationError(
                {
                    'montant_paye': _(
                        'Le montant (%(m)s %(dp)s) dépasse le solde restant (%(s)s %(dd)s) après conversion.'
                    )
                    % {
                        'm': montant,
                        'dp': devise_paiement.sigle,
                        's': dette.solde_restant,
                        'dd': dette_devise.sigle,
                    }
                }
            )
        attrs['devise_paiement'] = devise_paiement
        attrs['montant_applique_dette'] = montant_applique_dette
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
        devise = validated_data['devise_paiement']
        type_caisse = validated_data['type_caisse']
        moyen = validated_data.get('moyen') or ''
        reference = validated_data.get('reference') or ''
        req = self.context.get('request')
        tenant_id = getattr(req, 'tenant_id', None) if req else None
        branch_id = getattr(req, 'branch_id', None) if req else None
        if not tenant_id and req and req.user.is_authenticated and hasattr(req.user, 'get_entreprise_id'):
            tenant_id = req.user.get_entreprise_id(req)
        user = req.user if req and req.user.is_authenticated else None

        motif = moyen.strip() or (
            f"Paiement dette - {dette.client.nom if dette.client else ''} - {montant}"
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
            taux_conversion_explicite=validated_data.get('taux_change'),
            montant_applique=validated_data['montant_applique_dette'],
            devise_applique=dette.devise,
        )


class PaiementDetteGroupedWriteSerializer(serializers.Serializer):
    MODE_ANCIENNES_DETTES_D_ABORD = 'ANCIENNES_DETTES_D_ABORD'
    MODE_REPARTITION_CHOICES = [
        (MODE_ANCIENNES_DETTES_D_ABORD, _('Anciennes dettes d\'abord')),
    ]

    client_id = serializers.SlugRelatedField(
        slug_field='id', queryset=Client.objects.all(), source='client'
    )
    dettes = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        write_only=True,
    )
    payer_toutes = serializers.BooleanField(required=False, default=False)
    montant_paye = serializers.DecimalField(max_digits=12, decimal_places=5)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(), source='devise', required=False, allow_null=True
    )
    type_caisse_id = serializers.PrimaryKeyRelatedField(
        queryset=TypeCaisse.objects.filter(is_active=True),
        source='type_caisse',
        required=True,
    )
    mode_repartition = serializers.ChoiceField(choices=MODE_REPARTITION_CHOICES, default=MODE_ANCIENNES_DETTES_D_ABORD)
    commentaire = serializers.CharField(required=False, allow_blank=True, default='')
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

    def _context_ids(self):
        req = self.context.get('request')
        tenant_id = getattr(req, 'tenant_id', None) if req else None
        branch_id = getattr(req, 'branch_id', None) if req else None
        if not tenant_id and req and getattr(req.user, 'is_authenticated', False) and hasattr(req.user, 'get_entreprise_id'):
            tenant_id = req.user.get_entreprise_id(req)
        return tenant_id, branch_id

    def _dettes_queryset(self, *, client, tenant_id, branch_id):
        qs = DetteClient.objects.filter(
            client=client,
            entreprise_id=tenant_id,
        )
        if branch_id is not None:
            qs = qs.filter(succursale_id=branch_id)
        return qs

    def _compute_status(self, dette, new_solde):
        if new_solde <= 0:
            return 'PAYEE'
        today = timezone.now().date()
        if dette.date_echeance and dette.date_echeance < today:
            return 'RETARD'
        return 'EN_COURS'

    def validate(self, attrs):
        client = attrs['client']
        dette_ids = attrs.get('dettes') or []
        payer_toutes = attrs.get('payer_toutes', False)
        montant = attrs['montant_paye']
        type_caisse = attrs.get('type_caisse')
        devise = attrs.get('devise')
        tenant_id, branch_id = self._context_ids()

        if not tenant_id:
            raise serializers.ValidationError({'client_id': _('Contexte entreprise manquant.')})
        if montant <= 0:
            raise serializers.ValidationError({'montant_paye': _('Le montant doit ?tre positif.')})
        if not payer_toutes and not dette_ids:
            raise serializers.ValidationError({
                'dettes': _('S?lectionnez au moins une dette ou activez payer_toutes.')
            })
        if type_caisse is None:
            raise serializers.ValidationError({
                'type_caisse_id': _('Veuillez s?lectionner une caisse avant de valider cette op?ration.')
            })
        if not type_caisse.is_active:
            raise serializers.ValidationError({
                'type_caisse_id': _('Cette op?ration financi?re exige une caisse active.')
            })

        qs = self._dettes_queryset(client=client, tenant_id=tenant_id, branch_id=branch_id).exclude(statut='PAYEE')
        if payer_toutes:
            dettes = list(qs.order_by('date_creation', 'id'))
        else:
            dettes = list(qs.filter(pk__in=dette_ids).order_by('date_creation', 'id'))
            found_ids = {d.pk for d in dettes}
            missing_ids = [did for did in dette_ids if did not in found_ids]
            if missing_ids:
                raise serializers.ValidationError({
                    'dettes': _('Certaines dettes sont introuvables, d?j? pay?es ou hors p?rim?tre: %(ids)s')
                    % {'ids': ', '.join(str(x) for x in missing_ids)}
                })

        if not dettes:
            raise serializers.ValidationError({'dettes': _('Aucune dette ouverte ? payer pour ce client.')})

        payment_devise = devise or dettes[0].devise
        dette_devise = dettes[0].devise
        if payment_devise is None or dette_devise is None:
            raise serializers.ValidationError({'devise_id': _('Devise requise pour ce paiement groupé.')})

        total_selectionne = Decimal('0.00000')
        for dette in dettes:
            dette_row_devise = dette.devise or dette_devise
            if dette_row_devise is None or dette_row_devise.pk != dette_devise.pk:
                raise serializers.ValidationError({
                    'dettes': _('Toutes les dettes sélectionnées doivent être dans la même devise.')
                })
            total_selectionne += dette.solde_restant

        if payment_devise.pk == dette_devise.pk:
            montant_equivalent_dette = montant
        else:
            try:
                montant_equivalent_dette, _ = payment_equivalent_in_dette_currency(
                    montant,
                    payment_devise,
                    dette_devise,
                    entreprise_id=tenant_id,
                )
            except Exception as exc:
                raise serializers.ValidationError({'devise_id': str(exc)}) from exc

        if montant_equivalent_dette > total_selectionne:
            raise serializers.ValidationError({
                'montant_paye': _('Le montant (%(m)s) dépasse le total sélectionné (%(s)s) après conversion.')
                % {'m': montant, 's': total_selectionne}
            })

        attrs['payment_devise'] = payment_devise
        attrs['dette_devise'] = dette_devise
        attrs['montant_equivalent_dette'] = montant_equivalent_dette
        attrs['total_selectionne'] = total_selectionne
        attrs['selected_dette_ids'] = [d.pk for d in dettes]
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        client = validated_data['client']
        dette_ids = validated_data['selected_dette_ids']
        montant = validated_data['montant_paye']
        payment_devise = validated_data['payment_devise']
        dette_devise = validated_data['dette_devise']
        montant_equivalent_dette = validated_data['montant_equivalent_dette']
        type_caisse = validated_data['type_caisse']
        commentaire = (validated_data.get('commentaire') or '').strip()
        moyen = (validated_data.get('moyen') or '').strip()
        mode_repartition = validated_data['mode_repartition']
        tenant_id, branch_id = self._context_ids()
        req = self.context.get('request')
        user = req.user if req and getattr(req.user, 'is_authenticated', False) else None

        dettes = list(
            DetteClient.objects.select_for_update()
            .filter(pk__in=dette_ids, client=client, entreprise_id=tenant_id)
            .order_by('date_creation', 'id')
        )
        if branch_id is not None:
            dettes = [d for d in dettes if d.succursale_id == branch_id]
        if not dettes:
            raise serializers.ValidationError({'dettes': _('Aucune dette ouverte ? payer pour ce client.')})

        total_selectionne = Decimal('0.00000')
        for dette in dettes:
            if dette.statut == 'PAYEE' or dette.solde_restant <= 0:
                raise serializers.ValidationError({
                    "dettes": _("La dette #%(id)s n'est plus ouverte.") % {"id": dette.pk}
                })
            row_devise = dette.devise or dette_devise
            if row_devise is None or row_devise.pk != dette_devise.pk:
                raise serializers.ValidationError({
                    'dettes': _('Toutes les dettes sélectionnées doivent être dans la même devise.')
                })
            total_selectionne += dette.solde_restant

        if montant_equivalent_dette > total_selectionne:
            raise serializers.ValidationError({
                'montant_paye': _('Le montant (%(m)s) dépasse le total sélectionné (%(s)s).')
                % {'m': montant, 's': total_selectionne}
            })

        reference = (validated_data.get('reference') or '').strip()
        if not reference:
            reference = f"PAY-GROUP-{tenant_id or 'NA'}-{client.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        remaining_dette = montant_equivalent_dette
        remaining_payment = montant
        dettes_payees = []
        mouvements = []

        for dette in dettes:
            if remaining_dette <= 0 or remaining_payment <= 0:
                break
            ancien_solde = dette.solde_restant
            montant_applique_dette = min(ancien_solde, remaining_dette)
            if montant_applique_dette <= 0:
                continue

            if payment_devise.pk == dette_devise.pk:
                montant_applique_paiement = montant_applique_dette
            else:
                from stock.services.currency import convert_amount, get_exchange_rate
                rate_dette_to_payment = get_exchange_rate(
                    dette_devise, payment_devise, entreprise_id=tenant_id,
                )
                montant_applique_paiement = convert_amount(montant_applique_dette, rate_dette_to_payment)
                montant_applique_paiement = min(montant_applique_paiement, remaining_payment)

            motif = commentaire or f"Paiement groupe des dettes - {client.nom} - Dette #{dette.pk}"
            mc = creer_mouvement_caisse(
                montant=montant_applique_paiement,
                devise=payment_devise,
                type_mouvement='ENTREE',
                entreprise_id=tenant_id,
                succursale_id=branch_id,
                content_object=dette,
                utilisateur=user,
                reference_piece=reference,
                motif=motif,
                moyen=moyen or None,
                type_caisse=type_caisse,
                categorie='PAIEMENT_DETTE',
                montant_applique=montant_applique_dette,
                devise_applique=dette_devise,
            )
            mouvements.append(mc)

            new_solde = ancien_solde - montant_applique_dette
            nouveau_statut = self._compute_status(dette, new_solde)
            DetteClient.objects.filter(pk=dette.pk).update(statut=nouveau_statut)

            dettes_payees.append({
                'dette_id': dette.pk,
                'sortie_id': dette.sortie_id,
                'mouvement_caisse_id': mc.pk,
                'montant_applique': str(montant_applique_dette),
                'montant_paiement': str(montant_applique_paiement),
                'ancien_solde': str(ancien_solde),
                'nouveau_solde': str(new_solde),
                'statut': nouveau_statut,
            })
            remaining_dette -= montant_applique_dette
            remaining_payment -= montant_applique_paiement

        return {
            'success': True,
            'message': _('Paiement groupé enregistré avec succès.'),
            'client': {
                'id': client.pk,
                'nom': client.nom,
            },
            'paiement': {
                'reference': reference,
                'montant_total_paye': str(montant),
                'devise': payment_devise.sigle if payment_devise else None,
                'devise_id': payment_devise.pk if payment_devise else None,
                'type_caisse_id': type_caisse.pk,
                'mode_repartition': mode_repartition,
                'nombre_dettes_selectionnees': len(dettes),
                'total_selectionne': str(total_selectionne),
                'montant_non_applique': str(remaining_payment),
            },
            'dettes_payees': dettes_payees,
            'paiements_crees': [
                {
                    'mouvement_caisse_id': mc.pk,
                    'dette_id': mc.object_id,
                    'reference': mc.reference_piece or '',
                    'montant_paye': str(mc.montant),
                }
                for mc in mouvements
            ],
        }


PaiementDetteSerializer = PaiementDetteReadSerializer


class ConversionPreviewSerializer(serializers.Serializer):
    """Prévisualisation conversion opération → devise caisse (source de vérité backend)."""

    montant = serializers.DecimalField(max_digits=14, decimal_places=5)
    devise_id = serializers.PrimaryKeyRelatedField(queryset=Devise.objects.all(), source='devise')
    type_caisse_id = serializers.PrimaryKeyRelatedField(
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


class PaiementDettePreviewSerializer(serializers.Serializer):
    """Prévisualisation paiement dette avec conversion éventuelle."""

    dette_id = serializers.PrimaryKeyRelatedField(queryset=DetteClient.objects.all(), source='dette')
    montant_paye = serializers.DecimalField(max_digits=12, decimal_places=5)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(), source='devise', required=False, allow_null=True,
    )
    type_caisse_id = serializers.PrimaryKeyRelatedField(
        queryset=TypeCaisse.objects.filter(is_active=True),
        source='type_caisse',
    )
    taux_change = serializers.DecimalField(max_digits=20, decimal_places=8, required=False, allow_null=True)

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
        montant = attrs['montant_paye']
        devise_paiement = attrs.get('devise') or dette.devise
        dette_devise = dette.devise
        if montant <= 0:
            raise serializers.ValidationError({'montant_paye': _('Le montant doit être positif.')})
        if not devise_paiement or not dette_devise:
            raise serializers.ValidationError({'devise_id': _('Devise requise.')})

        req = self.context.get('request')
        tenant_id = getattr(req, 'tenant_id', None) if req else None
        if not tenant_id and req and getattr(req.user, 'is_authenticated', False):
            tenant_id = req.user.get_entreprise_id(req)

        if devise_paiement.pk == dette_devise.pk:
            equivalent_dette = montant
            taux_paiement_dette = None
        else:
            try:
                equivalent_dette, taux_paiement_dette = payment_equivalent_in_dette_currency(
                    montant,
                    devise_paiement,
                    dette_devise,
                    entreprise_id=tenant_id,
                    explicit_rate=attrs.get('taux_change'),
                )
            except Exception as exc:
                raise serializers.ValidationError({'devise_id': str(exc)}) from exc

        attrs['devise_paiement'] = devise_paiement
        attrs['equivalent_dette'] = equivalent_dette
        attrs['taux_paiement_dette'] = taux_paiement_dette
        attrs['tenant_id'] = tenant_id
        return attrs

    def build_preview(self) -> dict:
        attrs = self.validated_data
        dette = attrs['dette']
        montant = attrs['montant_paye']
        devise_paiement = attrs['devise_paiement']
        equivalent_dette = attrs['equivalent_dette']
        ancien_solde = dette.solde_restant
        nouveau_solde = max(Decimal('0'), ancien_solde - equivalent_dette)
        excedent = max(Decimal('0'), equivalent_dette - ancien_solde)

        try:
            caisse_preview = prepare_caisse_movement(
                montant_operation=montant,
                devise_operation=devise_paiement,
                type_caisse=attrs['type_caisse'],
                entreprise_id=attrs['tenant_id'],
                explicit_conversion_rate=attrs.get('taux_change'),
            )
        except CaisseError as exc:
            raise serializers.ValidationError({'detail': str(exc)}) from exc

        return {
            'dette': {
                'id': dette.pk,
                'devise': {'id': dette.devise_id, 'sigle': dette.devise.sigle},
                'solde_avant': str(ancien_solde),
                'equivalent_regle': str(equivalent_dette),
                'solde_apres': str(nouveau_solde),
                'excedent': str(excedent),
            },
            'paiement': {
                'montant_paye': str(montant),
                'devise': {'id': devise_paiement.pk, 'sigle': devise_paiement.sigle},
                'taux_paiement_vers_dette': (
                    str(attrs['taux_paiement_dette']) if attrs.get('taux_paiement_dette') is not None else None
                ),
            },
            'caisse': caisse_preview.to_dict(),
            'type_caisse': {
                'id': attrs['type_caisse'].pk,
                'nom': attrs['type_caisse'].nom,
                'libelle': attrs['type_caisse'].libelle_affiche,
            },
            'conversion_appliquee': (
                devise_paiement.pk != dette.devise_id
                or caisse_preview.conversion_appliquee
            ),
        }
