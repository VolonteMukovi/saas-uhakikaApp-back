from decimal import Decimal

from rest_framework import serializers

from stock.models import InventaireLigne, InventaireSession
from stock.services import inventaire as inventaire_service
from stock.services.tenant_context import get_tenant_ids as _get_tenant_ids


class InventaireLigneSerializer(serializers.ModelSerializer):
    article_id = serializers.CharField(source='article.article_id', read_only=True)
    nom_scientifique = serializers.CharField(source='article.nom_scientifique', read_only=True)
    nom_commercial = serializers.CharField(source='article.nom_commercial', read_only=True)
    unite = serializers.CharField(source='article.unite.libelle', read_only=True)
    stock_theorique = serializers.SerializerMethodField()
    stock_physique = serializers.SerializerMethodField()
    ecart = serializers.SerializerMethodField()
    dernier_prix_unitaire = serializers.SerializerMethodField()
    montant_logiciel = serializers.SerializerMethodField()
    montant_physique = serializers.SerializerMethodField()
    ecart_montant = serializers.SerializerMethodField()

    class Meta:
        model = InventaireLigne
        fields = [
            'id',
            'article_id',
            'nom_scientifique',
            'nom_commercial',
            'unite',
            'stock_theorique',
            'stock_physique',
            'ecart',
            'dernier_prix_unitaire',
            'montant_logiciel',
            'montant_physique',
            'ecart_montant',
            'motif_ligne',
        ]
        read_only_fields = fields

    def _fmt(self, value):
        if value is None:
            return None
        return str(Decimal(str(value)).quantize(Decimal('0.00001')))

    def get_stock_theorique(self, obj):
        return self._fmt(obj.stock_theorique)

    def get_stock_physique(self, obj):
        return self._fmt(obj.stock_physique)

    def get_ecart(self, obj):
        return self._fmt(obj.ecart)

    def get_dernier_prix_unitaire(self, obj):
        return self._fmt(obj.dernier_prix_unitaire or 0)

    def get_montant_logiciel(self, obj):
        return self._fmt(obj.montant_logiciel)

    def get_montant_physique(self, obj):
        return self._fmt(obj.montant_physique)

    def get_ecart_montant(self, obj):
        return self._fmt(obj.ecart_montant)


class InventaireLigneUpdateSerializer(serializers.Serializer):
    stock_physique = serializers.DecimalField(max_digits=12, decimal_places=5, min_value=0)
    motif_ligne = serializers.CharField(required=False, allow_blank=True, default='')


class InventaireLigneBulkItemSerializer(serializers.Serializer):
    article_id = serializers.CharField()
    stock_physique = serializers.DecimalField(max_digits=12, decimal_places=5, min_value=0)
    motif_ligne = serializers.CharField(required=False, allow_blank=True, default='')


class InventaireLigneBulkSerializer(serializers.Serializer):
    lignes = InventaireLigneBulkItemSerializer(many=True)


class InventaireSessionListSerializer(serializers.ModelSerializer):
    resume = serializers.SerializerMethodField()
    cree_par_nom = serializers.SerializerMethodField()

    class Meta:
        model = InventaireSession
        fields = [
            'id',
            'libelle',
            'date_inventaire',
            'statut',
            'perimetre',
            'type_article_filtre',
            'commentaire',
            'date_creation',
            'date_demarrage',
            'date_validation',
            'cree_par_nom',
            'resume',
        ]

    def get_cree_par_nom(self, obj):
        if obj.cree_par:
            return obj.cree_par.get_full_name() or obj.cree_par.username
        return None

    def get_resume(self, obj):
        return inventaire_service.resume_session(obj)


class InventaireSessionDetailSerializer(InventaireSessionListSerializer):
    lignes = InventaireLigneSerializer(many=True, read_only=True)
    entree_ajustement_id = serializers.IntegerField(read_only=True, allow_null=True)
    sortie_ajustement_id = serializers.IntegerField(read_only=True, allow_null=True)
    valide_par_nom = serializers.SerializerMethodField()

    class Meta(InventaireSessionListSerializer.Meta):
        fields = InventaireSessionListSerializer.Meta.fields + [
            'lignes',
            'entree_ajustement_id',
            'sortie_ajustement_id',
            'valide_par_nom',
        ]

    def get_valide_par_nom(self, obj):
        if obj.valide_par:
            return obj.valide_par.get_full_name() or obj.valide_par.username
        return None


class InventaireSessionCreateSerializer(serializers.ModelSerializer):
    article_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        write_only=True,
        help_text='Codes articles pour périmètre PARTIEL.',
    )
    demarrer = serializers.BooleanField(
        default=False,
        write_only=True,
        help_text='Si true, génère immédiatement les lignes (statut EN_COURS).',
    )

    class Meta:
        model = InventaireSession
        fields = [
            'id',
            'libelle',
            'date_inventaire',
            'perimetre',
            'type_article_filtre',
            'commentaire',
            'article_ids',
            'demarrer',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        perimetre = attrs.get('perimetre', InventaireSession.PERIMETRE_EN_STOCK)
        article_ids = attrs.get('article_ids') or []
        if perimetre == InventaireSession.PERIMETRE_PARTIEL and not article_ids:
            raise serializers.ValidationError({
                'article_ids': 'Obligatoire pour le périmètre PARTIEL.',
            })
        return attrs

    def create(self, validated_data):
        article_ids = validated_data.pop('article_ids', None)
        demarrer = validated_data.pop('demarrer', False)
        request = self.context['request']
        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        session = InventaireSession.objects.create(
            **validated_data,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            cree_par=request.user,
        )
        if demarrer:
            inventaire_service.demarrer_session(session, article_ids=article_ids)
            session.refresh_from_db()
        return session


class InventaireSessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventaireSession
        fields = ['libelle', 'date_inventaire', 'commentaire']

    def validate(self, attrs):
        if self.instance.statut not in (
            InventaireSession.STATUT_BROUILLON,
            InventaireSession.STATUT_EN_COURS,
        ):
            raise serializers.ValidationError('Cet inventaire ne peut plus être modifié.')
        return attrs


class InventaireDemarrerSerializer(serializers.Serializer):
    article_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
