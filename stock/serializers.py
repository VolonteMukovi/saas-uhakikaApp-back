from rest_framework import serializers
from .models import (
    Entreprise,
    Succursale,
    Devise,
    TypeArticle,
    SousTypeArticle,
    Unite,
    Article,
    Entree,
    LigneEntree,
    Stock,
    Sortie,
    LigneSortie,
    LigneSortieLot,
    BeneficeLot,
    MouvementCaisse,
    Client,
    ClientEntreprise,
    DetteClient,
    TypeCaisse,
    DetailMouvementCaisse,
)
from django.db import transaction, models
from django.utils.translation import gettext as _

from order.services.lot_closure import entree_is_from_lot_closure

from stock.services.article_names import article_duplicate_exists, normalize_nom_scientifique
from stock.services.tenant_context import get_tenant_ids


class DeviseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Devise
        fields = '__all__'

class TypeArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeArticle
        fields = '__all__'
class SousTypeArticleSerializer(serializers.ModelSerializer):
    type_article = TypeArticleSerializer(read_only=True)
    type_article_id = serializers.PrimaryKeyRelatedField(queryset=TypeArticle.objects.all(), source='type_article', write_only=True)
    class Meta:
        model = SousTypeArticle
        fields = ['id', 'libelle', 'description', 'type_article', 'type_article_id']



class UniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unite
        fields = '__all__'


class ArticleSerializer(serializers.ModelSerializer):
    """
    Serializer pour Article.
    En lecture, les champs typeArticle et unite retournent l'objet complet (sérialisé),
    en écriture ils acceptent l'id.
    """
    sous_type_article = SousTypeArticleSerializer(read_only=True)
    sous_type_article_id = serializers.PrimaryKeyRelatedField(queryset=SousTypeArticle.objects.all(), source='sous_type_article', write_only=True)
    unite = UniteSerializer(read_only=True)
    unite_id = serializers.PrimaryKeyRelatedField(queryset=Unite.objects.all(), source='unite', write_only=True)

    type_article = serializers.SerializerMethodField(read_only=True)

    def get_type_article(self, obj):
        if obj.sous_type_article:
            return TypeArticleSerializer(obj.sous_type_article.type_article).data
        return None

    def validate_nom_scientifique(self, value):
        if value is None or not str(value).strip():
            raise serializers.ValidationError(_('Le nom scientifique est obligatoire.'))
        return ' '.join(str(value).split())

    def validate(self, attrs):
        request = self.context.get('request')
        nom = attrs.get('nom_scientifique')
        if self.instance is not None and nom is None:
            nom = self.instance.nom_scientifique
        if not nom:
            return attrs
        norm = normalize_nom_scientifique(nom)
        if not norm:
            raise serializers.ValidationError({
                'nom_scientifique': _('Le nom scientifique ne peut pas être vide ou ne contenir que des espaces.'),
            })
        if not request or not getattr(request, 'user', None) or not request.user.is_authenticated:
            return attrs
        tenant_id, branch_id = get_tenant_ids(request)
        if tenant_id is None:
            return attrs
        exclude_id = self.instance.pk if self.instance is not None else None
        if article_duplicate_exists(tenant_id, branch_id, norm, exclude_article_id=exclude_id):
            raise serializers.ValidationError({
                'nom_scientifique': _(
                    'Un article portant ce nom scientifique existe déjà pour votre entreprise '
                    'ou cette succursale. Modifiez le nom ou utilisez l’article existant.'
                ),
            })
        return attrs

    class Meta:
        model = Article
        fields = [
            'article_id',
            'nom_scientifique',
            'nom_commercial',
            'sous_type_article',
            'sous_type_article_id',
            'type_article',
            'unite',
            'unite_id',
        ]


class ArticleSearchSerializer(ArticleSerializer):
    """Article + score de pertinence (recherche FULLTEXT / fallback)."""

    relevance = serializers.FloatField(read_only=True)

    class Meta(ArticleSerializer.Meta):
        fields = ArticleSerializer.Meta.fields + ['relevance']


class EntrepriseSerializer(serializers.ModelSerializer):
    """
    CRUD entreprise. Tous les champs sont éditables par l'Admin (logo, email, slogan, etc.).
    Les mises à jour partielles (PATCH) sont supportées pour modifier un ou plusieurs champs.
    En lecture, `logo` est une URL absolue si `request` est dans le contexte (branding UI).
    """

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request is not None:
            if getattr(instance, 'logo', None) and instance.logo:
                try:
                    url = instance.logo.url
                    data['logo'] = (
                        request.build_absolute_uri(url)
                        if url and not url.startswith('http')
                        else url
                    )
                except ValueError:
                    data['logo'] = None
            else:
                data['logo'] = None
        return data

    class Meta:
        model = Entreprise
        fields = '__all__'


def entreprise_public_read_dict(entreprise, request=None):
    """
    Représentation lecture unique pour branding / auth / profil :
    même payload que GET /api/entreprises/{id}/ (EntrepriseSerializer + URL logo).
    """
    if entreprise is None:
        return None
    return EntrepriseSerializer(
        entreprise, context={'request': request} if request else {}
    ).data


class SuccursaleSerializer(serializers.ModelSerializer):
    """CRUD succursale (branch) d'une entreprise. L'entreprise est fixée par la vue (contexte tenant)."""
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)

    class Meta:
        model = Succursale
        fields = ['id', 'entreprise', 'entreprise_nom', 'nom', 'adresse', 'telephone', 'email', 'is_active', 'created_at']
        read_only_fields = ['created_at']
        extra_kwargs = {'entreprise': {'required': False}}


class LigneSortieSerializer(serializers.ModelSerializer):
    """
    Serializer pour LigneSortie.
    Le champ devise est OBLIGATOIRE et doit être fourni à la création/modification.
    En lecture, retourne l'objet complet de la devise et de l'article avec inner join.
    """
    article = ArticleSerializer(read_only=True)
    article_id = serializers.PrimaryKeyRelatedField(
        queryset=Article.objects.all(), 
        source='article', 
        write_only=True, 
        required=True
    )
    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(), 
        source='devise', 
        write_only=True, 
        required=True, 
        allow_null=False
    )

    lots_utilises = serializers.SerializerMethodField(read_only=True)
    benefices_lots = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = LigneSortie
        fields = [
            'id', 'article', 'article_id', 'quantite', 'prix_unitaire',
            'date_sortie', 'sortie', 'devise', 'devise_id', 
            'lots_utilises', 'benefices_lots'
        ]
        read_only_fields = ['date_sortie', 'sortie']
        # prix_unitaire n'est plus en read_only : il peut être fourni manuellement (prix réellement encaissé)
    
    def get_lots_utilises(self, obj):
        """Retourne les lots utilisés pour cette sortie"""
        from .models import LigneSortieLot
        lots = LigneSortieLot.objects.filter(ligne_sortie=obj)
        return [{
            'lot_id': lot.lot_entree.id,
            'quantite': lot.quantite,
            'prix_achat': str(lot.prix_achat),
            'prix_vente': str(lot.prix_vente),
            'benefice_unitaire': str(lot.benefice_unitaire),
            'benefice_total': str(lot.benefice_total),
        } for lot in lots]
    
    def get_benefices_lots(self, obj):
        """Retourne les bénéfices calculés pour cette sortie"""
        from .models import BeneficeLot
        benefices = BeneficeLot.objects.filter(ligne_sortie=obj)
        return [{
            'lot_id': b.lot_entree.id,
            'quantite_vendue': b.quantite_vendue,
            'prix_achat': str(b.prix_achat),
            'prix_vente': str(b.prix_vente),
            'benefice_unitaire': str(b.benefice_unitaire),
            'benefice_total': str(b.benefice_total),
            'statut': 'Gain' if b.benefice_total >= 0 else 'Perte',
        } for b in benefices]

    def validate(self, attrs):
        if not attrs.get('devise'):
            raise serializers.ValidationError(_('Le champ devise est obligatoire pour chaque ligne de sortie.'))
        return attrs


class ClientEntrepriseSerializer(serializers.ModelSerializer):
    client_id = serializers.CharField(source="client.id", read_only=True)
    client_nom = serializers.CharField(source="client.nom", read_only=True)
    entreprise_nom = serializers.CharField(source="entreprise.nom", read_only=True)
    succursale_nom = serializers.CharField(source="succursale.nom", read_only=True, allow_null=True)

    class Meta:
        model = ClientEntreprise
        fields = (
            "id",
            "client",
            "client_id",
            "client_nom",
            "entreprise",
            "entreprise_nom",
            "succursale",
            "succursale_nom",
            "is_special",
        )

    def validate(self, attrs):
        ent = attrs.get("entreprise") or (self.instance and self.instance.entreprise)
        suc = attrs.get("succursale", serializers.empty)
        if suc is serializers.empty:
            suc = self.instance.succursale if self.instance else None
        if suc is not None and ent is not None and suc.entreprise_id != ent.id:
            raise serializers.ValidationError(
                {"succursale": _("La succursale doit appartenir à l’entreprise du lien.")}
            )
        return attrs


class ClientLienWriteSerializer(serializers.ModelSerializer):
    """Création / remplacement des liens client ↔ entreprise."""

    class Meta:
        model = ClientEntreprise
        fields = ("entreprise", "succursale", "is_special")

    def validate(self, attrs):
        ent = attrs.get("entreprise")
        suc = attrs.get("succursale")
        if suc is not None and ent is not None and suc.entreprise_id != ent.id:
            raise serializers.ValidationError(
                {"succursale": _("La succursale doit appartenir à l’entreprise du lien.")}
            )
        return attrs


class ExistingClientReadSerializer(serializers.ModelSerializer):
    """Réponse riche lors d'une tentative de création d'un client dupliqué (email)."""

    liens_entreprise = ClientEntrepriseSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = (
            "id",
            "nom",
            "telephone",
            "adresse",
            "email",
            "date_enregistrement",
            "liens_entreprise",
        )


class ClientSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={"input_type": "password"},
        help_text="Mot de passe portail (connexion par e-mail). Laisser vide pour ne pas modifier.",
    )
    liens_entreprise = ClientEntrepriseSerializer(many=True, read_only=True)
    liens = ClientLienWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Client
        fields = [f.name for f in Client._meta.fields if f.name != "password"] + [
            "password",
            "liens_entreprise",
            "liens",
        ]

    def _assert_liens_tenant(self, liens_data, tenant_id):
        if tenant_id is None:
            return
        for row in liens_data:
            ent = row.get("entreprise")
            if ent is not None and ent.id != tenant_id:
                raise serializers.ValidationError(
                    {"liens": _("Chaque entreprise doit correspondre au contexte courant (JWT).")}
                )

    @transaction.atomic
    def create(self, validated_data):
        liens_in = validated_data.pop("liens", None)
        password = validated_data.pop("password", None)
        request = self.context.get("request")
        tenant_id, branch_id = get_tenant_ids(request) if request else (None, None)
        user = getattr(request, "user", None) if request else None
        if not (user and user.is_authenticated) and tenant_id is None:
            if not liens_in:
                raise serializers.ValidationError(
                    {
                        "liens": _(
                            "Sans connexion, indiquez au moins une entreprise : tableau « liens » "
                            "avec un objet contenant « entreprise » (id) et éventuellement « succursale »."
                        )
                    }
                )

        email = (validated_data.get("email") or "").strip()
        if email:
            existing = (
                Client.objects.filter(email__iexact=email)
                .prefetch_related("liens_entreprise__entreprise", "liens_entreprise__succursale")
                .first()
            )
            if existing is not None:
                already = set(existing.liens_entreprise.values_list("entreprise_id", flat=True))
                all_entreprises_qs = Entreprise.objects.all().order_by("id")
                entreprises_disponibles_qs = all_entreprises_qs.exclude(id__in=already)
                raise serializers.ValidationError(
                    {
                        "detail": _("Un client avec cet email existe déjà dans le système."),
                        "existing_client": ExistingClientReadSerializer(existing, context={"request": request}).data,
                        "suggestion": _(
                            "Si vous souhaitez créer un nouveau profil, veuillez utiliser une adresse email différente ainsi qu’un nom distinct."
                        ),
                        # Pour aider le frontend : toutes les entreprises existantes + celles non encore associées.
                        "entreprises_disponibles_ids": list(all_entreprises_qs.values_list("id", flat=True)),
                        "entreprises_disponibles": EntrepriseSerializer(
                            all_entreprises_qs, many=True, context={"request": request}
                        ).data,
                        "entreprises_non_associees_ids": list(
                            entreprises_disponibles_qs.values_list("id", flat=True)
                        ),
                        "entreprises_non_associees": EntrepriseSerializer(
                            entreprises_disponibles_qs, many=True, context={"request": request}
                        ).data,
                        "action": {
                            "endpoint": "/api/clients/associate-entreprise/",
                            "method": "POST",
                            "hint": _(
                                "Utilisez cet endpoint pour associer ce client existant à votre entreprise, sans le recréer."
                            ),
                        },
                    }
                )

        last_client = Client.objects.filter(id__startswith="CLI").order_by("-id").first()
        if last_client:
            try:
                last_num = int(last_client.id[3:])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        validated_data["id"] = f"CLI{new_num:04d}"

        instance = super().create(validated_data)

        if liens_in is not None:
            self._assert_liens_tenant(liens_in, tenant_id)
            for row in liens_in:
                ClientEntreprise.objects.create(client=instance, **row)
        elif tenant_id:
            ClientEntreprise.objects.create(
                client=instance,
                entreprise_id=tenant_id,
                succursale_id=branch_id,
                is_special=False,
            )

        if password and str(password).strip():
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        liens_in = validated_data.pop("liens", None)
        password = validated_data.pop("password", None)
        request = self.context.get("request")
        tenant_id, _ = get_tenant_ids(request) if request else (None, None)

        instance = super().update(instance, validated_data)
        if liens_in is not None:
            self._assert_liens_tenant(liens_in, tenant_id)
            instance.liens_entreprise.all().delete()
            for row in liens_in:
                ClientEntreprise.objects.create(client=instance, **row)

        if password is not None:
            if str(password).strip():
                instance.set_password(password)
                instance.save(update_fields=["password"])
            else:
                instance.password = None
                instance.save(update_fields=["password"])
        return instance


class ClientSearchSerializer(ClientSerializer):
    """Client + score de pertinence (recherche FULLTEXT / fallback)."""

    relevance = serializers.FloatField(read_only=True)

    class Meta(ClientSerializer.Meta):
        fields = [f.name for f in Client._meta.fields if f.name != "password"] + [
            "relevance",
            "liens_entreprise",
        ]


class SortieSerializer(serializers.ModelSerializer):
    """
    Serializer pour Sortie.
    Le champ devise est OBLIGATOIRE uniquement dans chaque ligne (lignes[*].devise).
    Le champ client est optionnel.
    """
    lignes = LigneSortieSerializer(many=True)
    client = ClientSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source='client',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Sortie
        fields = ['id', 'motif', 'statut', 'client', 'client_id', 'date_creation', 'lignes']
        read_only_fields = ['date_creation']

    @transaction.atomic
    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        user = self.context['request'].user

        sortie = Sortie.objects.create(
            motif=validated_data.get('motif', ''),
            statut=validated_data.get('statut', 'PAYEE'),
            client=validated_data.get('client'),
        )

        for ligne in lignes_data:
            article_obj = ligne['article']
            quantite = ligne['quantite']
            devise_id = ligne.get('devise')
            devise_obj = Devise.objects.get(pk=devise_id) if devise_id else None

            # Vérification stock disponible
            stock = Stock.objects.get(article=article_obj)
            if stock.Qte < quantite:
                raise serializers.ValidationError(
                    f"Stock insuffisant pour l’article {article_obj.nom} (Disponible: {stock.Qte}, Demandé: {quantite})"
                )

            # Création ligne avec devise
            LigneSortie.objects.create(
                sortie=sortie,
                article=article_obj,
                quantite=quantite,
                prix_unitaire=ligne.get('prix_unitaire'),
                devise=devise_obj
            )


            # Décrémenter le stock
            stock.Qte = models.F('Qte') - quantite
            stock.save()

        return sortie

    @transaction.atomic
    def update(self, instance, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        user = self.context['request'].user

        # Mise à jour des infos générales
        instance.motif = validated_data.get('motif', instance.motif)
        instance.save()

        # Rollback stock des anciennes lignes
        for old_ligne in instance.lignes.all():
            Stock.objects.filter(article=old_ligne.article).update(
                Qte=models.F('Qte') + old_ligne.quantite
            )
        instance.lignes.all().delete()

        # Re-créer nouvelles lignes
        for ligne in lignes_data:
            article_obj = ligne['article']
            quantite = ligne['quantite']
            devise_id = ligne.get('devise')
            devise_obj = Devise.objects.get(pk=devise_id) if devise_id else None

            stock = Stock.objects.get(article=article_obj)
            if stock.Qte < quantite:
                raise serializers.ValidationError(
                    f"Stock insuffisant pour l’article {article_obj.nom} (Disponible: {stock.Qte}, Demandé: {quantite})"
                )

            LigneSortie.objects.create(
                sortie=instance,
                article=article_obj,
                quantite=quantite,
                prix_unitaire=ligne.get('prix_unitaire'),
                devise=devise_obj
            )
            stock.Qte = models.F('Qte') - quantite
            stock.save()

        return instance


class StockSerializer(serializers.ModelSerializer):
    article = ArticleSerializer(read_only=True)
    
    # Champs calculés
    statut = serializers.SerializerMethodField()
    pourcentage_stock = serializers.SerializerMethodField()
    nom_complet = serializers.SerializerMethodField()
    type_article_nom = serializers.SerializerMethodField()
    sous_type_article_nom = serializers.SerializerMethodField()
    unite_nom = serializers.SerializerMethodField()
    date_expiration_proche = serializers.SerializerMethodField()
    date_expiration_formatee = serializers.SerializerMethodField()
    jours_avant_expiration = serializers.SerializerMethodField()
    
    class Meta:
        model = Stock
        fields = [
            'id',
            'article',
            'Qte',
            'seuilAlert',
            'statut',
            'pourcentage_stock',
            'nom_complet',
            'type_article_nom',
            'sous_type_article_nom',
            'unite_nom',
            'date_expiration_proche',
            'date_expiration_formatee',
            'jours_avant_expiration'
        ]
    
    def get_statut(self, obj):
        """Détermine le statut du stock : NORMAL, ALERTE, ou RUPTURE"""
        if obj.Qte == 0:
            return 'RUPTURE'
        elif obj.Qte <= obj.seuilAlert:
            return 'ALERTE'
        return 'NORMAL'
    
    def get_pourcentage_stock(self, obj):
        """Calcule le pourcentage de stock par rapport au seuil d'alerte"""
        if obj.seuilAlert == 0:
            return 100 if obj.Qte > 0 else 0
        return round((obj.Qte / obj.seuilAlert) * 100, 2)
    
    def get_nom_complet(self, obj):
        """Retourne le nom complet de l'article (scientifique + commercial si présent)"""
        nom = obj.article.nom_scientifique
        if obj.article.nom_commercial:
            nom += f" ({obj.article.nom_commercial})"
        return nom
    
    def get_type_article_nom(self, obj):
        """Retourne le nom du type d'article"""
        if obj.article.sous_type_article and obj.article.sous_type_article.type_article:
            return obj.article.sous_type_article.type_article.libelle
        return None
    
    def get_sous_type_article_nom(self, obj):
        """Retourne le nom du sous-type d'article"""
        if obj.article.sous_type_article:
            return obj.article.sous_type_article.libelle
        return None
    
    def get_unite_nom(self, obj):
        """Retourne le nom de l'unité"""
        if obj.article.unite:
            return obj.article.unite.libelle
        return None
    
    def get_entreprise_nom(self, obj):

        return None
    
    def get_date_expiration_proche(self, obj):
        """Retourne la date d'expiration la plus proche (la plus ancienne) des entrées de cet article"""
        from .models import LigneEntree
        ligne_entree = LigneEntree.objects.filter(
            article=obj.article,
      
            date_expiration__isnull=False
        ).order_by('date_expiration').first()
        
        if ligne_entree and ligne_entree.date_expiration:
            return ligne_entree.date_expiration
        return None
    
    def get_date_expiration_formatee(self, obj):
        """Retourne la date d'expiration formatée en français"""
        date_exp = self.get_date_expiration_proche(obj)
        if date_exp:
            return date_exp.strftime('%d/%m/%Y')
        return None
    
    def get_jours_avant_expiration(self, obj):
        """Calcule le nombre de jours avant expiration (négatif si expiré)"""
        from django.utils import timezone
        date_exp = self.get_date_expiration_proche(obj)
        if date_exp:
            delta = (date_exp - timezone.now().date()).days
            return delta
        return None



class LigneEntreeSerializer(serializers.ModelSerializer):
    """
    Serializer pour LigneEntree.
    Le champ devise est OBLIGATOIRE et doit être fourni à la création/modification.
    En lecture, retourne l'objet complet de la devise et de l'article avec inner join.
    """
    article = ArticleSerializer(read_only=True)
    article_id = serializers.PrimaryKeyRelatedField(
        queryset=Article.objects.all(), 
        source='article', 
        write_only=True, 
        required=True
    )
    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(), 
        source='devise', 
        write_only=True, 
        required=False, 
        allow_null=True
    )

    class Meta:
        model = LigneEntree
        fields = [
            'id', 'article', 'article_id', 'quantite', 'quantite_restante', 
            'prix_unitaire', 'prix_vente', 'date_entree', 'date_expiration', 
            'entree', 'devise', 'devise_id', 'seuil_alerte'
        ]
        read_only_fields = ['date_entree', 'entree', 'quantite_restante']

    def validate(self, attrs):
        # On ne valide plus devise obligatoire, la logique de fallback est gérée côté views
        # Le seuil d'alerte peut valoir 0, on vérifie uniquement l'existence (non-None)
        if attrs.get('seuil_alerte') is None:
            raise serializers.ValidationError({'seuil_alerte': _('Le seuil d\'alerte est obligatoire pour chaque ligne d\'entrée.')})

        # La quantité doit être fournie et strictement positive
        quantite = attrs.get('quantite')
        if quantite is None:
            raise serializers.ValidationError({'quantite': _('La quantité est obligatoire pour chaque ligne d\'entrée.')})
        try:
            if quantite <= 0:
                raise serializers.ValidationError({'quantite': _('La quantité doit être supérieure à 0.')})
        except TypeError:
            raise serializers.ValidationError({'quantite': _('La quantité doit être un nombre valide.')})

        return attrs






class EntreeSerializer(serializers.ModelSerializer):
    """
    Serializer pour Entree.
    Le champ devise est OBLIGATOIRE uniquement dans chaque ligne (lignes[*].devise).

    Entrée issue de la clôture d'un lot : ``lot_id`` renseigné, ``libele`` imposé côté serveur
    (non modifiable).
    """
    lignes = LigneEntreeSerializer(many=True)
    lot_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Entree
        fields = ['id', 'libele', 'description', 'date_op', 'lignes', 'lot_id']
        read_only_fields = ['date_op', 'lot_id']

    def get_lot_id(self, obj):
        from order.models import Lot

        return Lot.objects.filter(entree_stock_id=obj.pk).values_list('pk', flat=True).first()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = getattr(self, 'instance', None)
        if inst is not None and getattr(inst, 'pk', None) and entree_is_from_lot_closure(inst):
            self.fields['libele'].read_only = True
            self.fields['description'].read_only = True

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if entree_is_from_lot_closure(instance):
            data['description'] = ''
        return data

    def validate(self, attrs):
        inst = self.instance
        if inst is not None and getattr(inst, 'pk', None) and entree_is_from_lot_closure(inst):
            if 'libele' in attrs and attrs.get('libele') != inst.libele:
                raise serializers.ValidationError(
                    {'libele': _("Le libellé d'une entrée issue d'un lot clôturé ne peut pas être modifié.")}
                )
        return attrs

    def create(self, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        user = self.context['request'].user

        # Création de l'Entree
        entree = Entree.objects.create(
       
            libele=validated_data.get('libele', ''),
            description=validated_data.get('description', ''),
        )

        # Création des lignes et mise à jour du stock
        # Fallback devise principale si devise_id absent ou None
        devise_principale = Devise.objects.filter( est_principal=True).first()
        for ligne in lignes_data:
            article_obj = ligne['article']
            quantite = ligne['quantite']
            devise_id = ligne.get('devise_id')
            devise_obj = None
            if devise_id:
                try:
                    devise_obj = Devise.objects.get(pk=devise_id)
                except Devise.DoesNotExist:
                    devise_obj = devise_principale
            else:
                devise_obj = devise_principale
            LigneEntree.objects.create(
                entree=entree,
                article=article_obj,
                quantite=quantite,
                quantite_restante=quantite,  # Initialiser pour FIFO
                prix_unitaire=ligne.get('prix_unitaire'),
                prix_vente=ligne.get('prix_vente'),  # Prix de vente obligatoire
                date_expiration=ligne.get('date_expiration'),
                devise=devise_obj,
                seuil_alerte=ligne.get('seuil_alerte', 0)
            )
            Stock.objects.filter(article=article_obj).update(
                Qte=models.F('Qte') + quantite
            )

        return entree

    def update(self, instance, validated_data):
        lignes_data = validated_data.pop('lignes', [])
        user = self.context['request'].user

        # Mise à jour de l'entree
        instance.libele = validated_data.get('libele', instance.libele)
        instance.description = validated_data.get('description', instance.description)
        instance.save()

        # Rollback stock des anciennes lignes
        for old_ligne in instance.lignes.all():
            Stock.objects.filter(article=old_ligne.article).update(
                Qte=models.F('Qte') - old_ligne.quantite
            )

        # Suppression anciennes lignes
        instance.lignes.all().delete()

        # Création nouvelles lignes
        for ligne in lignes_data:
            article_obj = ligne['article']
            quantite = ligne['quantite']
            devise_id = ligne.get('devise')
            devise_obj = Devise.objects.get(pk=devise_id) if devise_id else None
            LigneEntree.objects.create(
                entree=instance,
                article=article_obj,
                quantite=quantite,
                quantite_restante=quantite,  # Initialiser pour FIFO
                prix_unitaire=ligne.get('prix_unitaire'),
                prix_vente=ligne.get('prix_vente'),  # Prix de vente obligatoire
                date_expiration=ligne.get('date_expiration'),
                devise=devise_obj,
                seuil_alerte=ligne.get('seuil_alerte', 0)
            )
            Stock.objects.filter(article=article_obj).update(
                Qte=models.F('Qte') + quantite
            )

        return instance




class TypeCaisseSerializer(serializers.ModelSerializer):
    """CRUD types de caisse (canal d'encaissement)."""

    class Meta:
        model = TypeCaisse
        fields = ['id', 'libelle', 'description', 'image', 'entreprise', 'succursale', 'is_active', 'created_at']
        read_only_fields = ['created_at', 'entreprise']


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
    Mouvement de caisse : montant, devise, type, ``motif``, ``moyen`` (logique simple, sans ventilation obligatoire).
    ``details`` en lecture seulement si d'anciennes lignes multicaisse existent encore en base.
    ``resume`` = même texte que ``motif_affiche`` (motif, ou anciens détails concaténés).
    """
    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(),
        source='devise',
        write_only=True,
        required=False,
        allow_null=False,
    )
    details = DetailMouvementCaisseSerializer(many=True, read_only=True)
    resume = serializers.SerializerMethodField(read_only=True)
    content_type_modele = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MouvementCaisse
        fields = [
            'id', 'date', 'montant', 'devise', 'devise_id', 'type', 'motif', 'moyen', 'resume',
            'content_type_modele', 'object_id', 'utilisateur', 'reference_piece', 'sortie', 'entree',
            'details',
        ]
        read_only_fields = ['id', 'date', 'object_id', 'utilisateur']

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

    def validate(self, attrs):
        m = attrs.get('montant')
        if m is not None and m < 0:
            raise serializers.ValidationError(_('Le montant ne peut pas être négatif.'))
        if not attrs.get('devise') and not self.instance:
            raise serializers.ValidationError(_('Le champ devise est obligatoire pour le mouvement de caisse.'))
        return attrs

    def to_internal_value(self, data):
        if hasattr(data, 'copy'):
            data = data.copy()
        else:
            data = dict(data)
        if 'devise' in data and 'devise_id' not in data:
            data['devise_id'] = data.pop('devise')
        return super().to_internal_value(data)

    @transaction.atomic
    def create(self, validated_data):
        from stock.services.caisse import creer_mouvement_caisse

        tenant_id = validated_data.pop('entreprise_id', None)
        branch_id = validated_data.pop('succursale_id', None)
        devise = validated_data.pop('devise')
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
        )


class DetteClientSerializer(serializers.ModelSerializer):
    client = ClientSerializer(read_only=True)
    client_id = serializers.SlugRelatedField(slug_field='id', queryset=Client.objects.all(), source='client', write_only=True)
    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(queryset=Devise.objects.all(), source='devise', write_only=True, required=False, allow_null=True)
    sortie = serializers.PrimaryKeyRelatedField(read_only=True)
    sortie_id = serializers.PrimaryKeyRelatedField(queryset=Sortie.objects.all(), source='sortie', write_only=True)
    # Remove SerializerMethodField to avoid recursion - will be added as a separate field only when needed
    paiements = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DetteClient
        fields = [
            'id', 'client', 'client_id', 'sortie', 'sortie_id', 'montant_total', 'montant_paye', 'solde_restant',
            'devise', 'devise_id', 'date_creation', 'date_echeance', 'statut', 'commentaire', 'paiements'
        ]
        read_only_fields = ['montant_paye', 'solde_restant', 'statut', 'date_creation']

    def validate_sortie(self, value):
        """
        Validation pour s'assurer que la sortie est EN_CREDIT avant de créer une dette.
        """
        if value.statut != 'EN_CREDIT':
            raise serializers.ValidationError(
                _("Impossible de créer une dette pour cette sortie. La sortie #%(pk)s a le statut '%(statut)s'. Seules les sorties avec le statut 'EN_CREDIT' peuvent générer une dette.")
                % {"pk": value.pk, "statut": value.statut}
            )
        return value

    def get_paiements(self, obj):
        if not self.context.get('include_paiements', True):
            return []
        try:
            from stock.services.caisse import mouvement_moyen_affiche

            qs = (
                obj._paiements_mouvements_qs()
                .select_related('devise', 'utilisateur')
                .prefetch_related('details__type_caisse')
                .order_by('-date')[:50]
            )
            out = []
            for p in qs:
                out.append({
                    'id': p.id,
                    'montant_paye': str(p.montant),
                    'date_paiement': p.date.isoformat() if p.date else None,
                    'moyen': mouvement_moyen_affiche(p),
                    'reference': p.reference_piece or '',
                    'mouvement_caisse_id': p.id,
                    'devise': (
                        {'id': p.devise.id, 'sigle': p.devise.sigle, 'symbole': p.devise.symbole}
                        if p.devise
                        else None
                    ),
                })
            return out
        except Exception:
            return []


class PaiementDetteReadSerializer(serializers.Serializer):
    """Représente un MouvementCaisse lié à une DetteClient (entrée de caisse, compat. API historique)."""

    def to_representation(self, mc):
        from stock.services.caisse import mouvement_moyen_affiche

        dette = None
        if mc.content_type_id and mc.object_id:
            from django.contrib.contenttypes.models import ContentType

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
        }


class PaiementDetteWriteSerializer(serializers.Serializer):
    dette_id = serializers.PrimaryKeyRelatedField(queryset=DetteClient.objects.all(), source='dette')
    montant_paye = serializers.DecimalField(max_digits=12, decimal_places=2)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(), source='devise', required=False, allow_null=True
    )
    moyen = serializers.CharField(required=False, allow_blank=True, default='')
    reference = serializers.CharField(required=False, allow_blank=True, default='')

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
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from stock.services.caisse import creer_mouvement_caisse

        dette = validated_data['dette']
        montant = validated_data['montant_paye']
        devise = validated_data.get('devise') or dette.devise
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
        )


# Alias pour les imports existants (liste / détail lecture)
PaiementDetteSerializer = PaiementDetteReadSerializer

# Méthode utilitaire pour total des dettes d'un client
class ClientDettesTotalSerializer(serializers.ModelSerializer):
    total_dettes = serializers.SerializerMethodField()
    class Meta:
        model = Client
        fields = ['id', 'nom', 'telephone', 'is_special', 'total_dettes']
    def get_total_dettes(self, obj):
        return sum([d.solde_restant for d in obj.dettes.all()])
