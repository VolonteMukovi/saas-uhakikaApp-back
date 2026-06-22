from rest_framework import serializers
from stock.models import Article, Stock, LigneEntree, Entree, InventaireLigne
from decimal import Decimal, ROUND_DOWN
from django.db.models import Sum, F
from django.utils.translation import gettext as _


def _dec(value, default='0'):
    try:
        return Decimal(str(value if value is not None else default))
    except Exception:
        return Decimal(default)


def _fmt_money(value):
    return str(_dec(value).quantize(Decimal('0.00001'), rounding=ROUND_DOWN))


def _stock_statut_code(qte, seuil):
    q = _dec(qte)
    s = _dec(seuil)
    if q <= 0:
        return 'RUPTURE'
    if s > 0 and q <= s:
        return 'ALERTE'
    return 'NORMAL'


def _stock_statut_label(code):
    return {
        'RUPTURE': _('RUPTURE'),
        'ALERTE': _('ALERTE'),
        'NORMAL': _('NORMAL'),
    }.get(code, code)


def _statut_ligne_code(stock_physique, ecart):
    if stock_physique is None:
        return 'NON_COMPTÉ'
    if ecart is None:
        return 'NON_COMPTÉ'
    ec = _dec(ecart)
    if ec == 0:
        return 'CONFORME'
    if ec > 0:
        return 'ECART_POSITIF'
    return 'ECART_NEGATIF'


def _statut_ligne_label(code):
    return {
        'NON_COMPTÉ': _('Non compté'),
        'NON_APPLICABLE': _('Non applicable'),
        'CONFORME': _('Conforme'),
        'ECART_POSITIF': _('Écart positif'),
        'ECART_NEGATIF': _('Écart négatif'),
    }.get(code, code)


def _seuil_article(article):
    stock = Stock.objects.filter(article=article).first()
    if stock is None:
        return Decimal('0')
    return _dec(stock.seuilAlert)


def _dernier_prix_achat(article) -> Decimal:
    """Dernier prix unitaire d'achat (dernière ligne d'entrée par date opération)."""
    last_line = (
        LigneEntree.objects.filter(article=article)
        .select_related('entree')
        .order_by('-entree__date_op', '-date_entree', '-id')
        .first()
    )
    if last_line is not None and last_line.prix_unitaire is not None:
        return _dec(last_line.prix_unitaire)
    return Decimal('0')


def _quantite_a_commander(qte, seuil) -> Decimal:
    """
    Quantité suggérée pour réapprovisionner jusqu'au seuil d'alerte.
    RUPTURE avec seuil : commander le seuil ; ALERTE : seuil - stock actuel.
    """
    q = _dec(qte)
    s = _dec(seuil)
    if s > 0 and q < s:
        return s - q
    if q <= 0 and s > 0:
        return s
    return Decimal('0')


INVENTAIRE_STATUTS_REFERENCE = {
    'stock': [
        {'code': 'NORMAL', 'libelle': str(_('NORMAL'))},
        {'code': 'ALERTE', 'libelle': str(_('ALERTE'))},
        {'code': 'RUPTURE', 'libelle': str(_('RUPTURE'))},
    ],
    'ligne': [
        {'code': 'NON_COMPTÉ', 'libelle': str(_('Non compté'))},
        {'code': 'NON_APPLICABLE', 'libelle': str(_('Non applicable'))},
        {'code': 'CONFORME', 'libelle': str(_('Conforme'))},
        {'code': 'ECART_POSITIF', 'libelle': str(_('Écart positif'))},
        {'code': 'ECART_NEGATIF', 'libelle': str(_('Écart négatif'))},
    ],
    'session': [
        {'code': 'BROUILLON', 'libelle': str(_('Brouillon'))},
        {'code': 'EN_COURS', 'libelle': str(_('En cours'))},
        {'code': 'VALIDE', 'libelle': str(_('Validé'))},
        {'code': 'ANNULE', 'libelle': str(_('Annulé'))},
    ],
}


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
    quantite_stock = serializers.SerializerMethodField()
    quantite = serializers.SerializerMethodField()
    Qte = serializers.SerializerMethodField()
    seuil_alerte = serializers.SerializerMethodField()
    statut = serializers.SerializerMethodField()
    statut_code = serializers.SerializerMethodField()
    statut_stock = serializers.SerializerMethodField()
    statut_stock_code = serializers.SerializerMethodField()
    stock_theorique = serializers.SerializerMethodField()
    stock_physique = serializers.SerializerMethodField()
    ecart = serializers.SerializerMethodField()
    statut_ligne = serializers.SerializerMethodField()
    statut_ligne_code = serializers.SerializerMethodField()
    prix_unitaire = serializers.SerializerMethodField()
    pu = serializers.SerializerMethodField()
    prix_total = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    def _qte(self, obj):
        return _dec(getattr(obj, 'Qte', 0))

    def _seuil(self, obj):
        return _dec(getattr(obj, 'seuilAlert', 0))

    def get_quantite_stock(self, obj):
        return _fmt_money(self._qte(obj))

    def get_quantite(self, obj):
        return self.get_quantite_stock(obj)

    def get_Qte(self, obj):
        return self.get_quantite_stock(obj)

    def get_seuil_alerte(self, obj):
        return _fmt_money(self._seuil(obj))

    def get_statut_code(self, obj):
        return self.get_statut_stock_code(obj)

    def get_statut(self, obj):
        return self.get_statut_stock(obj)

    def get_statut_stock_code(self, obj):
        return _stock_statut_code(self._qte(obj), self._seuil(obj))

    def get_statut_stock(self, obj):
        return str(_stock_statut_label(self.get_statut_stock_code(obj)))

    def get_stock_theorique(self, obj):
        return self.get_quantite_stock(obj)

    def get_stock_physique(self, obj):
        return None

    def get_ecart(self, obj):
        return None

    def get_statut_ligne_code(self, obj):
        return 'NON_APPLICABLE'

    def get_statut_ligne(self, obj):
        return str(_statut_ligne_label('NON_APPLICABLE'))

    def _resolve_prix_unitaire(self, obj):
        """Coût moyen pondéré des lots en stock (prix d'achat), sinon dernier PU d'entrée."""
        agg = LigneEntree.objects.filter(
            article=obj.article,
            quantite_restante__gt=0,
        ).aggregate(
            total_val=Sum(F('prix_unitaire') * F('quantite_restante')),
            total_qty=Sum('quantite_restante'),
        )
        total_qty = agg.get('total_qty') or 0
        total_val = agg.get('total_val')
        if total_qty and total_val is not None and total_val > 0:
            return total_val / Decimal(str(total_qty))
        last = (
            LigneEntree.objects.filter(article=obj.article)
            .order_by('-date_entree')
            .values('prix_unitaire')
            .first()
        )
        if last and last.get('prix_unitaire') is not None:
            return Decimal(str(last['prix_unitaire']))
        return Decimal('0')

    def get_prix_unitaire(self, obj):
        return _fmt_money(self._resolve_prix_unitaire(obj))

    def get_pu(self, obj):
        return self.get_prix_unitaire(obj)

    def get_prix_total(self, obj):
        pu = self._resolve_prix_unitaire(obj)
        return _fmt_money(pu * self._qte(obj))

    def get_total(self, obj):
        return self.get_prix_total(obj)


class RapportInventaireSessionLigneSerializer(serializers.ModelSerializer):
    """Ligne du rapport d'inventaire liée à une session opérationnelle."""

    article_id = serializers.CharField(source='article.article_id', read_only=True)
    nom_scientifique = serializers.CharField(source='article.nom_scientifique', read_only=True)
    nom_commercial = serializers.CharField(source='article.nom_commercial', read_only=True)
    type_article = serializers.CharField(
        source='article.sous_type_article.type_article.libelle', read_only=True,
    )
    sous_type = serializers.CharField(source='article.sous_type_article.libelle', read_only=True)
    unite = serializers.CharField(source='article.unite.libelle', read_only=True)
    stock_theorique = serializers.SerializerMethodField()
    stock_physique = serializers.SerializerMethodField()
    ecart = serializers.SerializerMethodField()
    quantite = serializers.SerializerMethodField()
    quantite_stock = serializers.SerializerMethodField()
    Qte = serializers.SerializerMethodField()
    seuil_alerte = serializers.SerializerMethodField()
    statut = serializers.SerializerMethodField()
    statut_code = serializers.SerializerMethodField()
    statut_stock = serializers.SerializerMethodField()
    statut_stock_code = serializers.SerializerMethodField()
    statut_ligne = serializers.SerializerMethodField()
    statut_ligne_code = serializers.SerializerMethodField()
    prix_unitaire = serializers.SerializerMethodField()
    pu = serializers.SerializerMethodField()
    prix_total = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    motif_ligne = serializers.CharField(read_only=True)

    class Meta:
        model = InventaireLigne
        fields = [
            'id', 'article_id', 'nom_scientifique', 'nom_commercial',
            'type_article', 'sous_type', 'unite',
            'stock_theorique', 'stock_physique', 'ecart',
            'quantite', 'quantite_stock', 'Qte', 'seuil_alerte',
            'statut', 'statut_code', 'statut_stock', 'statut_stock_code',
            'statut_ligne', 'statut_ligne_code',
            'prix_unitaire', 'pu', 'prix_total', 'total', 'motif_ligne',
        ]

    def _fmt(self, value):
        if value is None:
            return None
        return _fmt_money(value)

    def get_stock_theorique(self, obj):
        return self._fmt(obj.stock_theorique)

    def get_stock_physique(self, obj):
        return self._fmt(obj.stock_physique)

    def get_ecart(self, obj):
        return self._fmt(obj.ecart)

    def get_quantite(self, obj):
        return self.get_stock_theorique(obj)

    def get_quantite_stock(self, obj):
        return self.get_stock_theorique(obj)

    def get_Qte(self, obj):
        return self.get_stock_theorique(obj)

    def get_seuil_alerte(self, obj):
        return self._fmt(_seuil_article(obj.article))

    def get_statut_stock_code(self, obj):
        return _stock_statut_code(obj.stock_theorique, _seuil_article(obj.article))

    def get_statut_stock(self, obj):
        return str(_stock_statut_label(self.get_statut_stock_code(obj)))

    def get_statut_code(self, obj):
        return self.get_statut_stock_code(obj)

    def get_statut(self, obj):
        return self.get_statut_stock(obj)

    def get_statut_ligne_code(self, obj):
        return _statut_ligne_code(obj.stock_physique, obj.ecart)

    def get_statut_ligne(self, obj):
        return str(_statut_ligne_label(self.get_statut_ligne_code(obj)))

    def _resolve_prix_unitaire(self, obj):
        agg = LigneEntree.objects.filter(
            article=obj.article,
            quantite_restante__gt=0,
        ).aggregate(
            total_val=Sum(F('prix_unitaire') * F('quantite_restante')),
            total_qty=Sum('quantite_restante'),
        )
        total_qty = agg.get('total_qty') or 0
        total_val = agg.get('total_val')
        if total_qty and total_val is not None and total_val > 0:
            return total_val / Decimal(str(total_qty))
        last = (
            LigneEntree.objects.filter(article=obj.article)
            .order_by('-date_entree')
            .values('prix_unitaire')
            .first()
        )
        if last and last.get('prix_unitaire') is not None:
            return Decimal(str(last['prix_unitaire']))
        return Decimal('0')

    def get_prix_unitaire(self, obj):
        return _fmt_money(self._resolve_prix_unitaire(obj))

    def get_pu(self, obj):
        return self.get_prix_unitaire(obj)

    def get_prix_total(self, obj):
        pu = self._resolve_prix_unitaire(obj)
        qte = obj.stock_physique if obj.stock_physique is not None else obj.stock_theorique
        return _fmt_money(pu * _dec(qte))

    def get_total(self, obj):
        return self.get_prix_total(obj)


class BonEntreeArticleSerializer(serializers.Serializer):
    """
    Serializer pour le rapport de réquisition (préparation des achats).
    Stock actuel, dernier PU d'achat, quantité suggérée et montant estimé calculés côté API.
    """
    designation = serializers.SerializerMethodField()
    unite = serializers.CharField(source='article.unite.libelle')
    article_id = serializers.CharField(source='article.article_id')
    stock_actuel = serializers.SerializerMethodField()
    quantite_en_stock = serializers.SerializerMethodField()
    quantite_stock = serializers.SerializerMethodField()
    quantite = serializers.SerializerMethodField()
    Qte = serializers.SerializerMethodField()
    quantite_a_commander = serializers.SerializerMethodField()
    seuil_alerte = serializers.SerializerMethodField()
    statut_stock = serializers.SerializerMethodField()
    statut = serializers.SerializerMethodField()
    statut_code = serializers.SerializerMethodField()
    dernier_prix = serializers.SerializerMethodField()
    prix_unitaire = serializers.SerializerMethodField()
    pu = serializers.SerializerMethodField()
    montant_estime = serializers.SerializerMethodField()
    prix_total = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    def get_designation(self, obj):
        nom = obj.article.nom_scientifique
        if obj.article.nom_commercial:
            nom += f" ({obj.article.nom_commercial})"
        return nom

    def _qte(self, obj):
        return _dec(getattr(obj, 'Qte', 0))

    def _seuil(self, obj):
        return _dec(getattr(obj, 'seuilAlert', 0))

    def _pu(self, obj):
        return _dernier_prix_achat(obj.article)

    def _qte_commande(self, obj):
        return _quantite_a_commander(self._qte(obj), self._seuil(obj))

    def get_stock_actuel(self, obj):
        return _fmt_money(self._qte(obj))

    def get_quantite_en_stock(self, obj):
        return self.get_stock_actuel(obj)

    def get_quantite_stock(self, obj):
        return self.get_stock_actuel(obj)

    def get_quantite(self, obj):
        """Alias stock actuel (colonne « Qté en stock »)."""
        return self.get_stock_actuel(obj)

    def get_Qte(self, obj):
        return self.get_stock_actuel(obj)

    def get_quantite_a_commander(self, obj):
        return _fmt_money(self._qte_commande(obj))

    def get_seuil_alerte(self, obj):
        return _fmt_money(self._seuil(obj))

    def get_statut_code(self, obj):
        return _stock_statut_code(self._qte(obj), self._seuil(obj))

    def get_statut(self, obj):
        return str(_stock_statut_label(self.get_statut_code(obj)))

    def get_statut_stock(self, obj):
        code = self.get_statut_code(obj)
        if code == 'RUPTURE':
            return _("RUPTURE - Urgent")
        if code == 'ALERTE':
            return _("ALERTE - À réapprovisionner")
        return _("NORMAL")

    def get_dernier_prix(self, obj):
        return _fmt_money(self._pu(obj))

    def get_prix_unitaire(self, obj):
        return self.get_dernier_prix(obj)

    def get_pu(self, obj):
        return self.get_prix_unitaire(obj)

    def get_montant_estime(self, obj):
        montant = self._pu(obj) * self._qte_commande(obj)
        return _fmt_money(montant)

    def get_prix_total(self, obj):
        return self.get_montant_estime(obj)

    def get_total(self, obj):
        return self.get_montant_estime(obj)


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
    quantite = serializers.DecimalField(max_digits=12, decimal_places=5)
    prix_unitaire = serializers.DecimalField(max_digits=10, decimal_places=5)
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
        return _fmt_money(Decimal(str(obj.quantite)) * obj.prix_unitaire)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['quantite'] = _fmt_money(instance.quantite)
        data['prix_unitaire'] = _fmt_money(instance.prix_unitaire)
        data['pu'] = data['prix_unitaire']
        data['montant_ligne'] = data['prix_total']
        data['total'] = data['prix_total']
        return data
    
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
    total_montant = serializers.DecimalField(max_digits=14, decimal_places=5)
