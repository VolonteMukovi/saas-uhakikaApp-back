from decimal import Decimal

from rest_framework import serializers

from stock.models import Requisition, RequisitionHistorique, RequisitionLigne, Succursale
from stock.services import requisition as requisition_service
from stock.services.tenant_context import get_tenant_ids as _get_tenant_ids


class RequisitionHistoriqueSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = RequisitionHistorique
        fields = [
            'id',
            'action',
            'detail',
            'ancien_statut',
            'nouveau_statut',
            'utilisateur_nom',
            'date_action',
            'metadata',
        ]
        read_only_fields = fields

    def get_utilisateur_nom(self, obj):
        if obj.utilisateur:
            return obj.utilisateur.get_full_name() or obj.utilisateur.username
        return None


class RequisitionLigneSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return requisition_service.ligne_to_api_dict(instance)


class RequisitionLigneWriteSerializer(serializers.Serializer):
    type_ligne = serializers.ChoiceField(
        choices=RequisitionLigne.TYPE_CHOICES,
        required=False,
        default=RequisitionLigne.TYPE_ARTICLE,
    )
    article_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    designation = serializers.CharField(required=False, allow_blank=True, max_length=255)
    quantite = serializers.DecimalField(max_digits=12, decimal_places=5, required=False, min_value=Decimal('0.00001'))
    unite = serializers.CharField(required=False, allow_blank=True, default='')
    prix_estime = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    remarque = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        type_ligne = attrs.get('type_ligne') or RequisitionLigne.TYPE_ARTICLE
        if type_ligne == RequisitionLigne.TYPE_LIBRE:
            if not (attrs.get('designation') or '').strip():
                raise serializers.ValidationError({'designation': 'Obligatoire pour une ligne libre.'})
            if attrs.get('quantite') is None:
                raise serializers.ValidationError({'quantite': 'Obligatoire pour une ligne libre.'})
        else:
            if not attrs.get('article_id'):
                raise serializers.ValidationError({'article_id': 'Obligatoire pour une ligne article.'})
        return attrs


class RequisitionLigneUpdateSerializer(serializers.Serializer):
    designation = serializers.CharField(required=False, allow_blank=False, max_length=255)
    quantite = serializers.DecimalField(max_digits=12, decimal_places=5, required=False, min_value=Decimal('0.00001'))
    unite = serializers.CharField(required=False, allow_blank=True)
    prix_estime = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    remarque = serializers.CharField(required=False, allow_blank=True)
    ordre = serializers.IntegerField(required=False, min_value=0)


class RequisitionReorderSerializer(serializers.Serializer):
    ordre = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class RequisitionSuggestionsSerializer(serializers.Serializer):
    sources = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=['rupture', 'alerte'],
    )
    replace = serializers.BooleanField(required=False, default=False)


class RequisitionStatutSerializer(serializers.Serializer):
    motif = serializers.CharField(required=False, allow_blank=True, default='')
    commentaires = serializers.CharField(required=False, allow_blank=True, default='')


class RequisitionListSerializer(serializers.ModelSerializer):
    cree_par_nom = serializers.SerializerMethodField()
    valide_par_nom = serializers.SerializerMethodField()
    succursale_nom = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()
    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    priorite_libelle = serializers.CharField(source='get_priorite_display', read_only=True)
    est_modifiable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Requisition
        fields = [
            'id',
            'numero',
            'titre',
            'priorite',
            'priorite_libelle',
            'statut',
            'statut_libelle',
            'date_creation',
            'date_modification',
            'date_validation',
            'cree_par_nom',
            'valide_par_nom',
            'succursale',
            'succursale_nom',
            'archived',
            'est_modifiable',
            'resume',
        ]

    def get_cree_par_nom(self, obj):
        if obj.cree_par:
            return obj.cree_par.get_full_name() or obj.cree_par.username
        return None

    def get_valide_par_nom(self, obj):
        if obj.valide_par:
            return obj.valide_par.get_full_name() or obj.valide_par.username
        return None

    def get_succursale_nom(self, obj):
        return obj.succursale.nom if obj.succursale_id else None

    def get_resume(self, obj):
        return requisition_service.resume_requisition(obj)


class RequisitionDetailSerializer(RequisitionListSerializer):
    description = serializers.CharField(read_only=True)
    observations = serializers.CharField(read_only=True)
    commentaires = serializers.CharField(read_only=True)
    motif_rejet = serializers.CharField(read_only=True)
    date_rejet = serializers.DateTimeField(read_only=True)
    date_cloture = serializers.DateTimeField(read_only=True)
    lignes = RequisitionLigneSerializer(many=True, read_only=True)
    historique = RequisitionHistoriqueSerializer(many=True, read_only=True)
    actions_disponibles = serializers.SerializerMethodField()

    class Meta(RequisitionListSerializer.Meta):
        fields = RequisitionListSerializer.Meta.fields + [
            'description',
            'observations',
            'commentaires',
            'motif_rejet',
            'date_rejet',
            'date_cloture',
            'lignes',
            'historique',
            'actions_disponibles',
        ]

    def get_actions_disponibles(self, obj):
        s = obj.statut
        actions = ['imprimer', 'exporter_document']
        if obj.est_modifiable:
            actions.extend([
                'modifier', 'ajouter_ligne', 'supprimer_ligne', 'dupliquer_ligne',
                'reordonner', 'suggestions',
            ])
        if s == Requisition.STATUT_BROUILLON:
            actions.extend(['ouvrir', 'preparer', 'soumettre', 'annuler', 'supprimer'])
        elif s == Requisition.STATUT_OUVERTE:
            actions.extend(['preparer', 'soumettre', 'annuler', 'revenir_brouillon'])
        elif s == Requisition.STATUT_EN_PREPARATION:
            actions.extend(['soumettre', 'annuler', 'ouvrir'])
        elif s == Requisition.STATUT_EN_ATTENTE_VALIDATION:
            actions.extend(['valider', 'rejeter', 'annuler', 'preparer'])
        elif s == Requisition.STATUT_VALIDEE:
            actions.extend(['cloturer', 'annuler'])
        elif s == Requisition.STATUT_REJETEE:
            actions.extend(['reouvrir', 'annuler'])
        return sorted(set(actions))


class RequisitionCreateSerializer(serializers.Serializer):
    titre = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    observations = serializers.CharField(required=False, allow_blank=True, default='')
    commentaires = serializers.CharField(required=False, allow_blank=True, default='')
    priorite = serializers.ChoiceField(
        choices=Requisition.PRIORITE_CHOICES,
        required=False,
        default=Requisition.PRIORITE_NORMALE,
    )
    succursale_id = serializers.IntegerField(required=False, allow_null=True)
    avec_suggestions = serializers.BooleanField(required=False, default=False)
    sources = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=['rupture', 'alerte'],
    )

    def create(self, validated_data):
        request = self.context['request']
        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            raise serializers.ValidationError({'detail': 'Contexte entreprise manquant.'})
        succursale_id = validated_data.get('succursale_id')
        if succursale_id is None:
            succursale_id = branch_id
        if succursale_id is not None:
            if not Succursale.objects.filter(pk=succursale_id, entreprise_id=tenant_id).exists():
                raise serializers.ValidationError({'succursale_id': 'Succursale invalide.'})
        user = request.user if request.user.is_authenticated else None
        return requisition_service.create_requisition(
            entreprise_id=tenant_id,
            succursale_id=succursale_id,
            titre=validated_data['titre'],
            cree_par=user,
            description=validated_data.get('description') or '',
            observations=validated_data.get('observations') or '',
            commentaires=validated_data.get('commentaires') or '',
            priorite=validated_data.get('priorite') or Requisition.PRIORITE_NORMALE,
            avec_suggestions=bool(validated_data.get('avec_suggestions')),
            sources=validated_data.get('sources') or ['rupture', 'alerte'],
        )


class RequisitionUpdateSerializer(serializers.Serializer):
    titre = serializers.CharField(required=False, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    observations = serializers.CharField(required=False, allow_blank=True)
    commentaires = serializers.CharField(required=False, allow_blank=True)
    priorite = serializers.ChoiceField(choices=Requisition.PRIORITE_CHOICES, required=False)

    def update(self, instance, validated_data):
        requisition_service.assert_requisition_editable(instance)
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        changed = []
        for field in ('titre', 'description', 'observations', 'commentaires', 'priorite'):
            if field in validated_data:
                val = validated_data[field]
                if field == 'titre':
                    val = (val or '').strip()
                    if not val:
                        raise serializers.ValidationError({'titre': 'Le titre est obligatoire.'})
                if getattr(instance, field) != val:
                    setattr(instance, field, val)
                    changed.append(field)
        if changed:
            instance.save()
            requisition_service.log_historique(
                instance,
                action='MODIFICATION',
                utilisateur=user,
                detail=f'Champs mis à jour : {", ".join(changed)}',
                metadata={'champs': changed},
            )
        return instance
