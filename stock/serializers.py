from rest_framework import serializers
from .models import (
    Entreprise, Devise, TypeArticle, SousTypeArticle, Unite, Article, Entree, LigneEntree, Stock, Sortie, LigneSortie, LigneSortieLot, BeneficeLot, MouvementCaisse, Client, DetteClient, PaiementDette
)
from django.db import transaction, models
from django.utils.translation import gettext as _


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

class EntrepriseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Entreprise
        fields = '__all__'


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



class ClientSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    
    class Meta:
        model = Client
        fields = '__all__'
    
    def create(self, validated_data):
        # Récupérer le dernier client de cette entreprise pour générer le nouvel ID
        last_client = Client.objects.filter(   
            id__startswith=f"CLI"
        ).order_by('-id').first()
        
        if last_client:
            # Extraire le numéro et incrémenter
            try:
                last_num = int(last_client.id[3:])  # CLI0001 -> 1
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1
        
        validated_data['id'] = f"CLI{new_num:04d}"
        return super().create(validated_data)


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


class UniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unite
        fields = '__all__'

class TypeArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypeArticle
        fields = '__all__'


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
    """
    lignes = LigneEntreeSerializer(many=True)

    class Meta:
        model = Entree
        fields = ['id', 'libele', 'description', 'date_op', 'lignes']
        read_only_fields = ['date_op']

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




class MouvementCaisseSerializer(serializers.ModelSerializer):
    """
    Serializer pour MouvementCaisse.
    En lecture, le champ devise retourne l'objet complet (sérialisé),
    en écriture il accepte l'id via devise_id OU devise (pour compatibilité frontend).
    """
    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(
        queryset=Devise.objects.all(), 
        source='devise', 
        write_only=True, 
        required=False, 
        allow_null=False
    )

    class Meta:
        model = MouvementCaisse
        fields = [
            'id','date','montant','devise','devise_id','type','motif','moyen','reference_piece','sortie','entree'
        ]
        read_only_fields = ['id','date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les devises par entreprise si on a accès au request
        if 'request' in self.context and hasattr(self.context['request'], 'user'):
            user = self.context['request'].user
            self.fields['devise_id'].queryset = Devise.objects.filter(est_principal=True)

    def validate(self, attrs):
        if attrs.get('montant') and attrs['montant'] <= 0:
            raise serializers.ValidationError(_('Le montant doit être > 0'))
        
        # Après to_internal_value, la devise devrait être dans attrs['devise']
        if not attrs.get('devise'):
            raise serializers.ValidationError(_('Le champ devise est obligatoire pour le mouvement de caisse.'))
        
        return attrs

    def to_internal_value(self, data):
        # Si le frontend envoie 'devise' au lieu de 'devise_id', on fait la conversion
        if 'devise' in data and 'devise_id' not in data:
            # Créer une copie modifiable des données
            if hasattr(data, 'copy'):
                data = data.copy()
            else:
                # Si c'est un dict normal ou QueryDict non mutable
                data = dict(data)
            
            # Convertir 'devise' en 'devise_id'
            data['devise_id'] = data.pop('devise')
        
        return super().to_internal_value(data)


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
        # Only fetch paiements if explicitly requested in context to avoid unnecessary queries
        if self.context.get('include_paiements', True):
            try:
                # Use prefetch_related if available, otherwise fetch normally
                if hasattr(obj, '_prefetched_objects_cache') and 'paiements' in obj._prefetched_objects_cache:
                    paiements = obj.paiements.all()
                else:
                    paiements = obj.paiements.select_related('devise').all()[:50]  # Limit to 50 to prevent huge responses
                
                return [{
                    'id': p.id,
                    'montant_paye': str(p.montant_paye),
                    'date_paiement': p.date_paiement.isoformat() if p.date_paiement else None,
                    'moyen': p.moyen,
                    'reference': p.reference,
                    'devise': {'id': p.devise.id, 'sigle': p.devise.sigle, 'symbole': p.devise.symbole} if p.devise else None
                } for p in paiements]
            except Exception as e:
                # If there's any error fetching paiements, return empty list to prevent recursion
                return []
        return []

class PaiementDetteSerializer(serializers.ModelSerializer):
    # Remove dette_info to avoid recursion, use simple fields instead
    dette_id = serializers.PrimaryKeyRelatedField(queryset=DetteClient.objects.all(), source='dette', write_only=True)
    dette = serializers.SerializerMethodField(read_only=True)
    devise = DeviseSerializer(read_only=True)
    devise_id = serializers.PrimaryKeyRelatedField(queryset=Devise.objects.all(), source='devise', write_only=True, required=False, allow_null=True)

    class Meta:
        model = PaiementDette
        fields = [
            'id', 'dette', 'dette_id', 'montant_paye', 'date_paiement', 'moyen', 'reference', 'utilisateur', 'devise', 'devise_id'
        ]
        read_only_fields = ['date_paiement', 'utilisateur']
    
    def get_dette(self, obj):
        # Return minimal dette info to avoid circular reference
        try:
            if self.context.get('include_dette_details', False):
                return {
                    'id': obj.dette.id,
                    'client_nom': obj.dette.client.nom if obj.dette.client else None,
                    'montant_total': str(obj.dette.montant_total),
                    'solde_restant': str(obj.dette.solde_restant),
                    'statut': obj.dette.statut
                }
            else:
                # Minimal info by default
                return {
                    'id': obj.dette.id,
                    'client_nom': obj.dette.client.nom if obj.dette.client else None,
                }
        except Exception:
            return None

# Méthode utilitaire pour total des dettes d'un client
class ClientDettesTotalSerializer(serializers.ModelSerializer):
    total_dettes = serializers.SerializerMethodField()
    class Meta:
        model = Client
        fields = ['id', 'nom', 'telephone', 'total_dettes']
    def get_total_dettes(self, obj):
        return sum([d.solde_restant for d in obj.dettes.all()])
