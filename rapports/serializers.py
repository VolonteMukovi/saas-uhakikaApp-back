from rest_framework import serializers
from stock.models import Article, Stock, LigneEntree, Entree
from decimal import Decimal
from django.db.models import Sum, F
from django.utils.translation import gettext as _


class InventaireArticleSerializer(serializers.Serializer):
    """
    Serializer pour l'inventaire des articles en stock.
    Affiche tous les produits disponibles pendant une période donnée.
    Prix unitaire = coût moyen pondéré des lots en stock (LigneEntree).
    Prix total = prix_unitaire × quantite_stock.
    """
    article_id = serializers.CharField(source='article.article_id')
    nom_scientifique = serializers.CharField(source='article.nom_scientifique')
    nom_commercial = serializers.CharField(source='article.nom_commercial')
    type_article = serializers.CharField(source='article.sous_type_article.type_article.libelle')
    sous_type = serializers.CharField(source='article.sous_type_article.libelle')
    unite = serializers.CharField(source='article.unite.libelle')
    quantite_stock = serializers.IntegerField(source='Qte')
    seuil_alerte = serializers.IntegerField(source='seuilAlert')
    statut = serializers.SerializerMethodField()
    prix_unitaire = serializers.SerializerMethodField()
    prix_total = serializers.SerializerMethodField()

    def get_statut(self, obj):
        """Détermine le statut du stock par rapport au seuil d'alerte"""
        if obj.Qte == 0:
            return _("RUPTURE")
        elif obj.Qte <= obj.seuilAlert:
            return _("ALERTE")
        else:
            return _("NORMAL")

    def get_prix_unitaire(self, obj):
        """Coût moyen pondéré des lots en stock (prix d'achat)."""
        agg = LigneEntree.objects.filter(
            article=obj.article,
            quantite_restante__gt=0
        ).aggregate(
            total_val=Sum(F('prix_unitaire') * F('quantite_restante')),
            total_qty=Sum('quantite_restante')
        )
        total_qty = agg.get('total_qty') or 0
        total_val = agg.get('total_val')
        if total_qty and total_val is not None and total_val > 0:
            return (total_val / total_qty).quantize(Decimal('0.01'))
        last = LigneEntree.objects.filter(article=obj.article).order_by('-date_entree').values('prix_unitaire').first()
        if last and last.get('prix_unitaire') is not None:
            return Decimal(str(last['prix_unitaire'])).quantize(Decimal('0.01'))
        return Decimal('0.00')

    def get_prix_total(self, obj):
        """Prix total = prix_unitaire × quantite_stock."""
        pu = self.get_prix_unitaire(obj)
        return (pu * Decimal(str(obj.Qte))).quantize(Decimal('0.01'))


class BonEntreeArticleSerializer(serializers.Serializer):
    """
    Serializer pour le rapport de réquisition.
    Liste les articles dont le stock est au seuil d'alerte pour approvisionnement.
    """
    designation = serializers.SerializerMethodField()
    unite = serializers.CharField(source='article.unite.libelle')
    quantite = serializers.CharField(default='', read_only=True)  # À remplir manuellement
    prix_total = serializers.CharField(default='', read_only=True)  # À remplir manuellement
    article_id = serializers.CharField(source='article.article_id')
    stock_actuel = serializers.IntegerField(source='Qte')
    seuil_alerte = serializers.IntegerField(source='seuilAlert')
    statut_stock = serializers.SerializerMethodField()
    dernier_prix = serializers.SerializerMethodField()

    def get_dernier_prix(self, obj):
        """Dernier prix unitaire au dernier approvisionnement (dernière entrée contenant cet article, par date opération)."""
        from stock.models import LigneEntree
        last_line = (
            LigneEntree.objects.filter(article=obj.article)
            .select_related('entree')
            .order_by('-entree__date_op', '-id')
            .first()
        )
        if last_line is not None and last_line.prix_unitaire is not None:
            return f"{last_line.prix_unitaire:.2f}"
        return ''
    
    def get_designation(self, obj):
        """Retourne la désignation complète de l'article"""
        nom = obj.article.nom_scientifique
        if obj.article.nom_commercial:
            nom += f" ({obj.article.nom_commercial})"
        return nom
    
    def get_statut_stock(self, obj):
        """Statut du stock"""
        if obj.Qte == 0:
            return _("RUPTURE - Urgent")
        elif obj.Qte <= obj.seuilAlert:
            return _("ALERTE - À réapprovisionner")
        else:
            return _("NORMAL")


class BonAchatSerializer(serializers.Serializer):
    """
    Serializer pour le bon d'achat (approvisionnements effectués).
    Liste tous les approvisionnements à partir d'une date donnée.
    Note: La devise est mentionnée uniquement si différente de la devise principale (en-tête).
    """
    numero_entree = serializers.IntegerField(source='entree.id')
    date_entree = serializers.DateTimeField()
    libelle_entree = serializers.CharField(source='entree.libele')
    article_id = serializers.CharField(source='article.article_id')
    designation = serializers.SerializerMethodField()
    unite = serializers.CharField(source='article.unite.libelle')
    quantite = serializers.IntegerField()
    prix_unitaire = serializers.DecimalField(max_digits=10, decimal_places=2)
    prix_total = serializers.SerializerMethodField()
    devise_sigle = serializers.SerializerMethodField()
    date_expiration = serializers.DateField(allow_null=True)
    
    def get_designation(self, obj):
        """Retourne la désignation complète de l'article"""
        nom = obj.article.nom_scientifique
        if obj.article.nom_commercial:
            nom += f" ({obj.article.nom_commercial})"
        return nom
    
    def get_prix_total(self, obj):
        """Calcule le prix total de la ligne"""
        return (Decimal(str(obj.quantite)) * obj.prix_unitaire).quantize(Decimal('0.01'))
    
    def get_devise_sigle(self, obj):
        """
        Retourne uniquement le sigle de la devise si elle est différente de la devise principale.
        Si c'est la devise principale, retourne None (elle est déjà dans l'en-tête).
        """
        if obj.devise:
            # Vérifier si c'est la devise principale
            if obj.devise.est_principal:
                return None  # Pas besoin de répéter, c'est dans l'en-tête
            return obj.devise.sigle
        return None


class RecapitulatifAchatSerializer(serializers.Serializer):
    """
    Serializer pour le récapitulatif des achats par devise.
    """
    devise_sigle = serializers.CharField()
    devise_symbole = serializers.CharField()
    nombre_lignes = serializers.IntegerField()
    total_montant = serializers.DecimalField(max_digits=14, decimal_places=2)
