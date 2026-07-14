import uuid

from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import check_password, is_password_usable, make_password
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum, F, OuterRef, Subquery, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
# Modèle Entreprise



class Entreprise(models.Model):
    nom = models.CharField(max_length=255)
    secteur = models.CharField(max_length=255)
    pays = models.CharField(max_length=100)
    adresse = models.CharField(max_length=255)
    telephone = models.CharField(max_length=50)
    email = models.EmailField()
    nif = models.CharField(max_length=100)
    responsable = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='entreprises/logos/', blank=True, null=True)
    slogan = models.CharField(max_length=255, blank=True, null=True, help_text="Devise ou slogan de l'entreprise (affiché dans l'en-tête des rapports)")
    has_branches = models.BooleanField(default=False, help_text="Active la gestion par succursales (branches).")
    configuration_complete = models.BooleanField(
        default=False,
        help_text="True lorsque les informations obligatoires de l'entreprise sont complétées (flow SaaS).",
    )
    config = models.TextField(
        blank=True,
        default='',
        help_text='Configuration JSON (apparence rapports, POS, UI…)',
    )

    def __str__(self):
        return self.nom

    def get_config_dict(self) -> dict:
        from rest_framework.exceptions import ValidationError as DRFValidationError

        from stock.services.entreprise_config import default_entreprise_config, parse_config_raw
        if not self.config or not str(self.config).strip():
            return default_entreprise_config()
        try:
            return parse_config_raw(self.config)
        except (DRFValidationError, ValueError, TypeError):
            return default_entreprise_config()

    def set_config_dict(self, data: dict) -> None:
        from stock.services.entreprise_config import serialize_config_dict
        self.config = serialize_config_dict(data)

    def merge_config(self, patch: dict, user_id: int | None = None) -> dict:
        from stock.services.entreprise_config import merge_config_dict
        current = self.get_config_dict()
        merged = merge_config_dict(current, patch, user_id=user_id)
        self.set_config_dict(merged)
        return merged


class Succursale(models.Model):
    """Succursale (branch) d'une entreprise (tenant)."""
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='succursales')
    nom = models.CharField(max_length=255)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entreprise', 'nom')
        ordering = ['entreprise_id', 'nom', 'id']

    def __str__(self):
        return f"{self.entreprise.nom} - {self.nom}"
    
class Unite(models.Model):
    libelle = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='unites', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='unites', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return self.libelle


class TypeArticle(models.Model):
    libelle = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='type_articles', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='type_articles', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return self.libelle


class SousTypeArticle(models.Model):
    type_article = models.ForeignKey(TypeArticle, on_delete=models.CASCADE, related_name='sous_types')
    libelle = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='sous_type_articles', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='sous_type_articles', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return self.libelle


class Article(models.Model):
    nom_scientifique = models.CharField(max_length=100)
    nom_commercial = models.CharField(max_length=100, blank=True, null=True)
    article_id = models.CharField(primary_key=True, max_length=10, unique=True, editable=False)
    sous_type_article = models.ForeignKey(SousTypeArticle, on_delete=models.CASCADE, default=1)
    unite = models.ForeignKey(Unite, on_delete=models.CASCADE)
    emplacement = models.CharField(max_length=200, default=1)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='articles', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='articles', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['succursale_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return self.nom_scientifique

    def save(self, *args, **kwargs):
        if self.nom_scientifique is not None:
            self.nom_scientifique = ' '.join(self.nom_scientifique.split())
        if not self.article_id:
            # Préfixe 4 lettres (2 type + 2 sous-type) : plusieurs sous-types peuvent partager le même
            # préfixe → l'ancien comptage par sous-type seul provoquait des 1062 (FOAG0001 deux fois).
            ta = (self.sous_type_article.type_article.libelle or 'XX')[:2].upper()
            st = (self.sous_type_article.libelle or 'XX')[:2].upper()
            prefix = f'{ta}{st}'
            qs = Article.objects.filter(article_id__startswith=prefix)
            if self.entreprise_id:
                qs = qs.filter(entreprise_id=self.entreprise_id)
            max_num = 0
            plen = len(prefix)
            for aid in qs.values_list('article_id', flat=True):
                if not aid or len(aid) <= plen:
                    continue
                try:
                    max_num = max(max_num, int(aid[plen:]))
                except ValueError:
                    continue
            next_n = max_num + 1
            if next_n > 9999:
                raise ValueError(
                    'Limite de codes article atteinte pour ce préfixe (9999). '
                    'Renommez un libellé de type ou sous-type pour obtenir un autre préfixe.'
                )
            self.article_id = f'{prefix}{str(next_n).zfill(4)}'
        super().save(*args, **kwargs)


class ConditionnementArticle(models.Model):
    """
    Définition des conditionnements possibles d'un article.
    Le prix n'est pas stocké ici : il est défini sur les approvisionnements (LigneEntree).
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='conditionnements')
    nom = models.CharField(max_length=100)
    multiplicateur_base = models.DecimalField(
        max_digits=12,
        decimal_places=5,
        default=Decimal('1'),
        help_text="Nombre d'unités de base contenues dans ce conditionnement.",
    )
    est_defaut = models.BooleanField(
        default=False,
        help_text="Conditionnement appliqué par défaut (ex: pièce/unité).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['article_id', '-est_defaut', 'nom', 'id']
        indexes = [
            models.Index(fields=['article', 'est_defaut']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['article', 'nom'],
                name='uniq_conditionnement_article_nom',
            ),
        ]

    def __str__(self):
        return f"{self.article_id} - {self.nom} x{self.multiplicateur_base}"

    def save(self, *args, **kwargs):
        if self.multiplicateur_base is None:
            self.multiplicateur_base = Decimal('1')
        self.multiplicateur_base = Decimal(str(self.multiplicateur_base))
        if self.multiplicateur_base <= 0:
            raise ValueError('Le multiplicateur du conditionnement doit être strictement positif.')
        if self.est_defaut:
            ConditionnementArticle.objects.filter(
                article_id=self.article_id,
                est_defaut=True,
            ).exclude(pk=self.pk).update(est_defaut=False)
        super().save(*args, **kwargs)


class CodeBarresArticle(models.Model):
    """
    Code-barres lié à un article et à un conditionnement précis (pièce, pack, carton…).
    Un code est unique par entreprise.
    """

    TYPE_EAN13 = 'EAN13'
    TYPE_EAN8 = 'EAN8'
    TYPE_UPC = 'UPC'
    TYPE_CODE128 = 'CODE128'
    TYPE_QR = 'QR'
    TYPE_INTERNE = 'INTERNE'
    TYPE_AUTRE = 'AUTRE'
    TYPE_CODE_CHOICES = [
        (TYPE_EAN13, 'EAN-13'),
        (TYPE_EAN8, 'EAN-8'),
        (TYPE_UPC, 'UPC'),
        (TYPE_CODE128, 'Code 128'),
        (TYPE_QR, 'QR'),
        (TYPE_INTERNE, 'Interne'),
        (TYPE_AUTRE, 'Autre'),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.CASCADE,
        related_name='codes_barres',
    )
    succursale = models.ForeignKey(
        Succursale,
        on_delete=models.CASCADE,
        related_name='codes_barres',
        null=True,
        blank=True,
    )
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='codes_barres',
    )
    conditionnement = models.ForeignKey(
        ConditionnementArticle,
        on_delete=models.PROTECT,
        related_name='codes_barres',
    )
    code = models.CharField(max_length=128)
    type_code = models.CharField(max_length=20, choices=TYPE_CODE_CHOICES, default=TYPE_INTERNE)
    est_principal = models.BooleanField(
        default=False,
        help_text="Code principal du conditionnement.",
    )
    est_actif = models.BooleanField(default=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='codes_barres_crees',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['article_id', 'conditionnement_id', '-est_principal', 'code']
        indexes = [
            models.Index(fields=['entreprise', 'code']),
            models.Index(fields=['entreprise', 'est_actif']),
            models.Index(fields=['article', 'conditionnement']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['entreprise', 'code'],
                name='uniq_code_barres_entreprise_code',
            ),
        ]

    def __str__(self):
        return f'{self.code} → {self.article_id} / {self.conditionnement.nom}'

    def save(self, *args, **kwargs):
        self.code = ''.join(str(self.code or '').strip().split())
        if not self.code:
            raise ValueError('Le code-barres ne peut pas être vide.')
        if self.conditionnement_id and self.article_id:
            if self.conditionnement.article_id != self.article_id:
                raise ValueError('Le conditionnement doit appartenir à l’article.')
        if self.est_principal and self.conditionnement_id:
            CodeBarresArticle.objects.filter(
                conditionnement_id=self.conditionnement_id,
                est_principal=True,
            ).exclude(pk=self.pk).update(est_principal=False)
        super().save(*args, **kwargs)


class Entree(models.Model):
    libele = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    date_op = models.DateTimeField(auto_now_add=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='entrees', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='entrees', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['succursale_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return f"Entree: {self.libele} ({self.date_op})"

class LigneEntree(models.Model):  
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    conditionnement = models.ForeignKey(
        ConditionnementArticle,
        on_delete=models.PROTECT,
        related_name='lignes_entree',
        null=True,
        blank=True,
    )
    quantite_saisie = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    quantite_base = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    quantite = models.DecimalField(max_digits=12, decimal_places=5)
    quantite_restante = models.DecimalField(max_digits=12, decimal_places=5,default=0, help_text="Quantité encore disponible dans ce lot (FIFO)")
    prix_achat_conditionnement = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    prix_vente_conditionnement = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    prix_achat_unitaire_base = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    prix_vente_unitaire_base = models.DecimalField(max_digits=10, decimal_places=5, null=True, blank=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=5, help_text="Prix d'achat unitaire")
    prix_vente = models.DecimalField(max_digits=10, decimal_places=5, help_text="Prix de vente unitaire défini à l'entrée")
    date_expiration = models.DateField(null=True, blank=True, help_text="Date d'expiration du produit (optionnelle)")
    date_entree = models.DateTimeField(auto_now_add=True)
    entree = models.ForeignKey(Entree, related_name='lignes', on_delete=models.CASCADE)
    # Devise de la ligne (nullable)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='ligneentrees', null=True, blank=True)
    devise_reference = models.ForeignKey(
        'Devise',
        on_delete=models.PROTECT,
        related_name='ligneentrees_reference',
        null=True,
        blank=True,
    )
    taux_change = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    montant_reference = models.DecimalField(max_digits=14, decimal_places=5, default=Decimal('0'))
    # Seuil d'alerte obligatoire pour chaque ligne d'entrée
    seuil_alerte = models.DecimalField(max_digits=12, decimal_places=5, help_text="Seuil d'alerte pour cet article",default=0)

    class Meta:
        ordering = ['date_entree', 'id']  # FIFO : plus ancien en premier
        indexes = [
            models.Index(fields=['article', 'date_entree']),  # Pour requêtes FIFO rapides
        ]

    def __str__(self):
        return f"LigneEntree: {self.article.nom_scientifique} x {self.quantite_restante}/{self.quantite} (Entree {self.entree.id})"
    
    def save(self, *args, **kwargs):
        if self.quantite_base is None:
            self.quantite_base = self.quantite
        if self.quantite_saisie is None:
            self.quantite_saisie = self.quantite
        if self.prix_achat_unitaire_base is None:
            self.prix_achat_unitaire_base = self.prix_unitaire
        if self.prix_vente_unitaire_base is None:
            self.prix_vente_unitaire_base = self.prix_vente
        if self.prix_achat_conditionnement is None:
            self.prix_achat_conditionnement = self.prix_unitaire
        if self.prix_vente_conditionnement is None:
            self.prix_vente_conditionnement = self.prix_vente
        # Initialiser quantite_restante à quantite si c'est une nouvelle entrée
        if self.pk is None:
            self.quantite_restante = self.quantite
        super().save(*args, **kwargs)


class PrixConditionnementEntree(models.Model):
    """
    Prix de vente spécifiques par conditionnement pour une ligne d'entrée (lot).
    """
    ligne_entree = models.ForeignKey(
        LigneEntree, on_delete=models.CASCADE, related_name='prix_conditionnements'
    )
    conditionnement = models.ForeignKey(
        ConditionnementArticle, on_delete=models.PROTECT, related_name='prix_ligne_entrees'
    )
    prix_vente = models.DecimalField(max_digits=10, decimal_places=5)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='prix_conditionnement_entrees')
    est_prix_principal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ligne_entree_id', '-est_prix_principal', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['ligne_entree', 'conditionnement'],
                name='uniq_prix_cond_par_ligne_entree',
            ),
        ]
        indexes = [
            models.Index(fields=['ligne_entree', 'conditionnement']),
            models.Index(fields=['devise']),
        ]

    def __str__(self):
        return f"Ligne {self.ligne_entree_id} - {self.conditionnement.nom}: {self.prix_vente}"


class Stock(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE)
    Qte = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    seuilAlert = models.DecimalField(max_digits=12, decimal_places=5, default=0)


    def __str__(self):
        return f"Stock de {self.article.nom_scientifique}"


# Sortie et LigneSortie
class Sortie(models.Model):
    motif = models.CharField(
        max_length=255,
        blank=True,
        help_text="Motif / commentaire de la sortie (hors caisse).",
    )
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, related_name='sorties', null=True, blank=True, help_text="Client associé à cette sortie (optionnel)")
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='sorties', null=True, blank=True)
    devise_reference = models.ForeignKey(
        'Devise',
        on_delete=models.PROTECT,
        related_name='sorties_reference',
        null=True,
        blank=True,
    )
    statut = models.CharField(
        max_length=20,
        choices=[
            ('EN_CREDIT', 'En crédit'),
            ('PAYEE', 'Payée'),
        ],
        default='PAYEE'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='sorties', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='sorties', null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['succursale_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
            models.Index(fields=['client_id', 'entreprise_id', '-date_creation']),
        ]

    def __str__(self):
        client_nom = self.client.nom if self.client else "Client Anonyme"
        return f"Sortie #{self.pk} - {client_nom}"


class Client(models.Model):
    id = models.CharField(primary_key=True, max_length=20)
    nom = models.CharField(max_length=150)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    password = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name="Mot de passe (hash)",
        help_text="Hash du mot de passe pour l’espace client (connexion par e-mail). Laisser vide si le client n’a pas accès au portail.",
    )
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.id} - {self.nom}"

    def set_password(self, raw_password: str) -> None:
        """Définit le mot de passe portail (stockage hashé, comme pour User)."""
        if raw_password is None or str(raw_password).strip() == "":
            self.password = None
            return
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        if not raw_password or not self.password:
            return False
        if not is_password_usable(self.password):
            return False
        return check_password(raw_password, self.password)

    def has_portal_password(self) -> bool:
        return bool(self.password and is_password_usable(self.password))


class ClientEntreprise(models.Model):
    """
    Association Client ↔ Entreprise (multi-tenant), avec succursale préférée optionnelle.
    Un même contact peut être lié à plusieurs entreprises sans dupliquer la fiche `Client`.
    """

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="liens_entreprise")
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name="liens_clients")
    succursale = models.ForeignKey(
        Succursale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="liens_clients",
        help_text="Succursale de rattachement pour ce client dans cette entreprise (optionnel).",
    )
    is_special = models.BooleanField(
        default=False,
        verbose_name="Client spécial",
        help_text="Priorité dans les rapports (dettes, etc.) pour ce client dans cette entreprise.",
    )

    class Meta:
        unique_together = ("client", "entreprise")
        indexes = [
            models.Index(fields=["entreprise_id", "client_id"]),
            models.Index(fields=["client_id"]),
            models.Index(fields=["entreprise_id", "is_special"]),
        ]

    def __str__(self) -> str:
        return f"{self.client_id} @ {self.entreprise_id}"


class DetteClientQuerySet(models.QuerySet):
    """Annotations pour filtres / rapports (montants depuis MouvementCaisse)."""

    def with_paiements_aggregate(self):
        from caisse.models import MouvementCaisse

        ct = ContentType.objects.get_for_model(DetteClient)
        paye_sq = (
            MouvementCaisse.objects.filter(
                content_type=ct,
                object_id=OuterRef('pk'),
                type='ENTREE',
            )
            .values('object_id')
            .annotate(
                total=Sum(
                    Coalesce(
                        F('montant_applique'),
                        F('montant'),
                        output_field=DecimalField(max_digits=14, decimal_places=5),
                    )
                )
            )
            .values('total')[:1]
        )
        return self.annotate(
            montant_paye_agg=Coalesce(
                Subquery(paye_sq, output_field=DecimalField(max_digits=14, decimal_places=5)),
                Value(Decimal('0.00')),
            ),
            solde_restant_agg=F('montant_total') - F('montant_paye_agg'),
        )


class DetteClient(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='dettes')
    sortie = models.OneToOneField('Sortie', on_delete=models.CASCADE, related_name='dette')
    montant_total = models.DecimalField(max_digits=12, decimal_places=5)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='dettes', null=True, blank=True)
    devise_reference = models.ForeignKey(
        'Devise',
        on_delete=models.PROTECT,
        related_name='dettes_reference',
        null=True,
        blank=True,
    )
    taux_change = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    montant_reference = models.DecimalField(max_digits=14, decimal_places=5, default=Decimal('0'))
    date_creation = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateField(blank=True, null=True, help_text="Date limite de paiement")
    statut = models.CharField(
        max_length=20,
        choices=[
            ('EN_COURS', 'En cours'),
            ('PAYEE', 'Payée'),
            ('RETARD', 'En retard')
        ],
        default='EN_COURS'
    )
    commentaire = models.TextField(blank=True, null=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='dettes_clients', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='dettes_clients', null=True, blank=True)

    objects = DetteClientQuerySet.as_manager()

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Dette client"
        verbose_name_plural = "Dettes clients"
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return f"Dette {self.client.nom} - {self.montant_total}{self.devise.sigle if self.devise else ''}"

    def save(self, *args, **kwargs):
        if not self.date_echeance:
            from datetime import timedelta
            self.date_echeance = timezone.now().date() + timedelta(days=30)
        super().save(*args, **kwargs)

    def _paiements_mouvements_qs(self):
        from caisse.models import MouvementCaisse

        ct = ContentType.objects.get_for_model(DetteClient)
        return MouvementCaisse.objects.filter(
            content_type=ct,
            object_id=self.pk,
            type='ENTREE',
        )

    @property
    def montant_paye(self) -> Decimal:
        total = Decimal('0.00')
        for mv in self._paiements_mouvements_qs():
            if mv.montant_applique is not None:
                total += mv.montant_applique
            else:
                total += mv.montant or Decimal('0.00')
        return total

    @property
    def solde_restant(self) -> Decimal:
        return (self.montant_total or Decimal('0.00')) - self.montant_paye


class LigneSortie(models.Model):
    
    sortie = models.ForeignKey(Sortie, related_name='lignes', on_delete=models.CASCADE)
    article = models.ForeignKey(Article, related_name='sorties', on_delete=models.CASCADE)
    quantite = models.DecimalField(max_digits=12, decimal_places=5)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=5, default=0, help_text="Prix réellement encaissé (peut différer du prix de vente du lot en cas de promotion/réduction)")
    date_sortie = models.DateTimeField(auto_now_add=True)
    # Devise de la ligne de sortie (nullable)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='lignesorties', null=True, blank=True)
    devise_reference = models.ForeignKey(
        'Devise',
        on_delete=models.PROTECT,
        related_name='lignesorties_reference',
        null=True,
        blank=True,
    )
    taux_change = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    montant_reference = models.DecimalField(max_digits=14, decimal_places=5, default=Decimal('0'))

    def __str__(self):
        return f"{self.quantite}×{self.article.nom_scientifique}"

    def get_cout_achat_unitaire(self):
        """
        Retourne le coût d'achat unitaire moyen de l'article au moment de la vente.
        Calculé à partir des lots utilisés (FIFO).
        """
        from django.db.models import Sum, F
        lots_utilises = self.lots_utilises.all()
        if lots_utilises.exists():
            total_cout = sum(lot.quantite * lot.lot_entree.prix_unitaire for lot in lots_utilises)
            total_quantite = sum(lot.quantite for lot in lots_utilises)
            if total_quantite > 0:
                return total_cout / total_quantite
        return Decimal('0.00')


class LigneSortieLot(models.Model):
    """
    Traçabilité FIFO : quels lots ont été utilisés pour chaque sortie.
    Permet de calculer les bénéfices précis par lot.
    """
    ligne_sortie = models.ForeignKey(LigneSortie, on_delete=models.CASCADE, related_name='lots_utilises')
    lot_entree = models.ForeignKey(LigneEntree, on_delete=models.CASCADE, related_name='sorties_utilisees')
    quantite = models.DecimalField(max_digits=12, decimal_places=5, help_text="Quantité prélevée de ce lot")
    prix_achat = models.DecimalField(max_digits=10, decimal_places=5, help_text="Prix d'achat du lot (copié)")
    prix_vente = models.DecimalField(max_digits=10, decimal_places=5, help_text="Prix de vente du lot (copié)")
    
    class Meta:
        verbose_name = "Lot utilisé dans sortie"
        verbose_name_plural = "Lots utilisés dans sorties"
        indexes = [
            models.Index(fields=['ligne_sortie', 'lot_entree']),
        ]

    def __str__(self):
        return f"{self.quantite}× lot #{self.lot_entree.id} pour sortie #{self.ligne_sortie.sortie.id}"
    
    @property
    def benefice_unitaire(self):
        """Bénéfice unitaire (prix vente - prix achat)"""
        return self.prix_vente - self.prix_achat
    
    @property
    def benefice_total(self):
        """Bénéfice total pour ce lot"""
        return self.benefice_unitaire * Decimal(str(self.quantite))


class BeneficeLot(models.Model):
    """
    Bénéfices calculés par lot pour analyse de performance.
    """
    lot_entree = models.ForeignKey(LigneEntree, on_delete=models.CASCADE, related_name='benefices')
    ligne_sortie = models.ForeignKey(LigneSortie, on_delete=models.CASCADE, related_name='benefices_lots', null=True, blank=True)
    quantite_vendue = models.DecimalField(max_digits=12, decimal_places=5)
    prix_achat = models.DecimalField(max_digits=10, decimal_places=5)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=5)
    benefice_unitaire = models.DecimalField(max_digits=10, decimal_places=5, help_text="Prix vente - Prix achat")
    benefice_total = models.DecimalField(max_digits=12, decimal_places=5, help_text="Bénéfice total pour cette quantité")
    date_calcul = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_calcul']
        verbose_name = "Bénéfice par lot"
        verbose_name_plural = "Bénéfices par lot"
    
    def __str__(self):
        statut = "Gain" if self.benefice_total >= 0 else "Perte"
        return f"{statut}: {self.benefice_total} pour lot #{self.lot_entree.id}"
    
    def save(self, *args, **kwargs):
        # Calcul automatique des bénéfices
        self.benefice_unitaire = self.prix_vente - self.prix_achat
        self.benefice_total = self.benefice_unitaire * Decimal(str(self.quantite_vendue))
        super().save(*args, **kwargs)

class Devise(models.Model):
    sigle = models.CharField(max_length=10)
    nom = models.CharField(max_length=100)
    symbole = models.CharField(max_length=10)
    est_principal = models.BooleanField(default=False)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='devises')

    class Meta:
        unique_together = ('sigle', 'entreprise')  # Unicité par entreprise
        verbose_name = 'Devise'
        verbose_name_plural = 'Devises'

    def save(self, *args, **kwargs):
        """
        Garantit qu'une seule devise soit principale par entreprise.
        Si est_principal=True, désactive automatiquement les autres devises principales.
        Si c'est la première devise de l'entreprise, la rend automatiquement principale.
        """
        # Si c'est une nouvelle devise et qu'aucune devise principale n'existe
        if self.pk is None:
            has_principal = Devise.objects.filter(
                entreprise_id=self.entreprise_id,
                est_principal=True
            ).exists()
            
            # Si aucune devise principale n'existe, forcer celle-ci à être principale
            if not has_principal:
                self.est_principal = True
        
        # Si cette devise devient principale, désactiver les autres
        if self.est_principal:
            Devise.objects.filter(
                entreprise_id=self.entreprise_id,
                est_principal=True
            ).exclude(pk=self.pk).update(est_principal=False)
        else:
            # Vérifier qu'il reste au moins une devise principale
            # (cas où on essaie de désactiver la seule devise principale)
            if self.pk:  # Si c'est une mise à jour
                old_instance = Devise.objects.filter(pk=self.pk).first()
                if old_instance and old_instance.est_principal:
                    # Cette devise était principale et on veut la rendre secondaire
                    autres_principales = Devise.objects.filter(
                        entreprise_id=self.entreprise_id,
                        est_principal=True
                    ).exclude(pk=self.pk).exists()
                    
                    if not autres_principales:
                        # Promouvoir automatiquement une autre devise
                        autre_devise = Devise.objects.filter(
                            entreprise_id=self.entreprise_id,
                        ).exclude(pk=self.pk).first()
                        
                        if autre_devise:
                            autre_devise.est_principal = True
                            autre_devise.save()
        
        super().save(*args, **kwargs)

    def __str__(self):
        principal_str = " [PRINCIPALE]" if self.est_principal else ""
        return f"{self.nom} ({self.sigle}){principal_str} - {self.entreprise.nom}"


class TauxChange(models.Model):
    devise_source = models.ForeignKey(
        Devise,
        on_delete=models.CASCADE,
        related_name='taux_sortants',
    )
    devise_cible = models.ForeignKey(
        Devise,
        on_delete=models.CASCADE,
        related_name='taux_entrants',
    )
    taux = models.DecimalField(max_digits=20, decimal_places=8)
    date_application = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='taux_change_crees',
    )
    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.CASCADE,
        related_name='taux_change',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_application', '-id']
        indexes = [
            models.Index(fields=['entreprise_id', 'is_active']),
            models.Index(fields=['entreprise_id', 'devise_source_id', 'devise_cible_id']),
            models.Index(fields=['entreprise_id', 'date_application']),
        ]
        verbose_name = 'Taux de change'
        verbose_name_plural = 'Taux de change'

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.devise_source_id == self.devise_cible_id:
            raise ValidationError('Les devises source et cible doivent etre differentes.')
        if self.devise_source and self.devise_source.entreprise_id != self.entreprise_id:
            raise ValidationError('La devise source doit appartenir a la meme entreprise.')
        if self.devise_cible and self.devise_cible.entreprise_id != self.entreprise_id:
            raise ValidationError('La devise cible doit appartenir a la meme entreprise.')
        if self.taux is None or self.taux <= 0:
            raise ValidationError('Le taux de change doit etre strictement positif.')

    def __str__(self):
        return f"1 {self.devise_source.sigle} = {self.taux} {self.devise_cible.sigle}"


class InventaireSession(models.Model):
    """Session d'inventaire physique : comparaison stock théorique vs stock compté."""

    STATUT_BROUILLON = 'BROUILLON'
    STATUT_EN_COURS = 'EN_COURS'
    STATUT_VALIDE = 'VALIDE'
    STATUT_ANNULE = 'ANNULE'
    STATUT_CHOICES = [
        (STATUT_BROUILLON, 'Brouillon'),
        (STATUT_EN_COURS, 'En cours'),
        (STATUT_VALIDE, 'Validé'),
        (STATUT_ANNULE, 'Annulé'),
    ]

    PERIMETRE_COMPLET = 'COMPLET'
    PERIMETRE_EN_STOCK = 'EN_STOCK'
    PERIMETRE_PARTIEL = 'PARTIEL'
    PERIMETRE_CHOICES = [
        (PERIMETRE_COMPLET, 'Catalogue complet'),
        (PERIMETRE_EN_STOCK, 'Articles en stock uniquement'),
        (PERIMETRE_PARTIEL, 'Liste d\'articles'),
    ]

    libelle = models.CharField(max_length=200)
    date_inventaire = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_BROUILLON)
    perimetre = models.CharField(max_length=20, choices=PERIMETRE_CHOICES, default=PERIMETRE_EN_STOCK)
    type_article_filtre = models.CharField(max_length=100, blank=True, default='')
    commentaire = models.TextField(blank=True, default='')
    entreprise = models.ForeignKey(
        Entreprise, on_delete=models.CASCADE, related_name='inventaires',
    )
    succursale = models.ForeignKey(
        Succursale, on_delete=models.CASCADE, related_name='inventaires',
        null=True, blank=True,
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventaires_crees',
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventaires_valides',
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_demarrage = models.DateTimeField(null=True, blank=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    entree_ajustement = models.ForeignKey(
        'Entree', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventaires_ajustement_positif',
    )
    sortie_ajustement = models.ForeignKey(
        'Sortie', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventaires_ajustement_negatif',
    )

    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['entreprise_id', 'statut']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return f"Inventaire #{self.pk} — {self.libelle} ({self.get_statut_display()})"


class InventaireLigne(models.Model):
    """Ligne d'inventaire : stock théorique figé + stock physique saisi."""

    session = models.ForeignKey(
        InventaireSession, on_delete=models.CASCADE, related_name='lignes',
    )
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='lignes_inventaire')
    stock_theorique = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    stock_physique = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    ecart = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    motif_ligne = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['article__nom_scientifique', 'article_id']
        unique_together = ('session', 'article')
        indexes = [
            models.Index(fields=['session_id', 'article_id']),
        ]

    def __str__(self):
        return f"{self.article_id} th={self.stock_theorique} ph={self.stock_physique}"

    def recalculer_ecart(self):
        if self.stock_physique is None:
            self.ecart = None
        else:
            self.ecart = self.stock_physique - self.stock_theorique
        return self.ecart


class Requisition(models.Model):
    """Document de travail indépendant pour préparer un approvisionnement."""

    STATUT_BROUILLON = 'BROUILLON'
    STATUT_OUVERTE = 'OUVERTE'
    STATUT_EN_PREPARATION = 'EN_PREPARATION'
    STATUT_EN_ATTENTE_VALIDATION = 'EN_ATTENTE_VALIDATION'
    STATUT_VALIDEE = 'VALIDEE'
    STATUT_REJETEE = 'REJETEE'
    STATUT_ANNULEE = 'ANNULEE'
    STATUT_CLOTUREE = 'CLOTUREE'
    STATUT_CHOICES = [
        (STATUT_BROUILLON, 'Brouillon'),
        (STATUT_OUVERTE, 'Ouverte'),
        (STATUT_EN_PREPARATION, 'En préparation'),
        (STATUT_EN_ATTENTE_VALIDATION, 'En attente de validation'),
        (STATUT_VALIDEE, 'Validée'),
        (STATUT_REJETEE, 'Rejetée'),
        (STATUT_ANNULEE, 'Annulée'),
        (STATUT_CLOTUREE, 'Clôturée'),
    ]
    STATUTS_VERROUILLES = {
        STATUT_VALIDEE,
        STATUT_ANNULEE,
        STATUT_CLOTUREE,
    }
    STATUTS_MODIFIABLES = {
        STATUT_BROUILLON,
        STATUT_OUVERTE,
        STATUT_EN_PREPARATION,
        STATUT_EN_ATTENTE_VALIDATION,
        STATUT_REJETEE,
    }

    PRIORITE_BASSE = 'BASSE'
    PRIORITE_NORMALE = 'NORMALE'
    PRIORITE_HAUTE = 'HAUTE'
    PRIORITE_URGENTE = 'URGENTE'
    PRIORITE_CHOICES = [
        (PRIORITE_BASSE, 'Basse'),
        (PRIORITE_NORMALE, 'Normale'),
        (PRIORITE_HAUTE, 'Haute'),
        (PRIORITE_URGENTE, 'Urgente'),
    ]

    numero = models.CharField(max_length=32, db_index=True)
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    observations = models.TextField(blank=True, default='')
    commentaires = models.TextField(blank=True, default='')
    priorite = models.CharField(
        max_length=20, choices=PRIORITE_CHOICES, default=PRIORITE_NORMALE,
    )
    statut = models.CharField(
        max_length=32, choices=STATUT_CHOICES, default=STATUT_BROUILLON,
    )
    entreprise = models.ForeignKey(
        Entreprise, on_delete=models.CASCADE, related_name='requisitions',
    )
    succursale = models.ForeignKey(
        Succursale, on_delete=models.CASCADE, related_name='requisitions',
        null=True, blank=True,
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitions_creees',
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitions_validees',
    )
    rejete_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitions_rejetees',
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_rejet = models.DateTimeField(null=True, blank=True)
    date_cloture = models.DateTimeField(null=True, blank=True)
    motif_rejet = models.TextField(blank=True, default='')
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_creation']
        verbose_name = 'Réquisition'
        verbose_name_plural = 'Réquisitions'
        constraints = [
            models.UniqueConstraint(
                fields=['entreprise', 'numero'],
                name='uniq_requisition_entreprise_numero',
            ),
        ]
        indexes = [
            models.Index(fields=['entreprise_id', 'statut']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
            models.Index(fields=['entreprise_id', 'priorite']),
            models.Index(fields=['entreprise_id', 'cree_par_id']),
            models.Index(fields=['entreprise_id', 'date_creation']),
        ]

    def __str__(self):
        return f'{self.numero} — {self.titre} ({self.get_statut_display()})'

    @property
    def est_modifiable(self) -> bool:
        return self.statut in self.STATUTS_MODIFIABLES and not self.archived


class RequisitionLigne(models.Model):
    """Ligne de réquisition : article catalogue ou ligne libre (hors stock)."""

    TYPE_ARTICLE = 'ARTICLE'
    TYPE_LIBRE = 'LIBRE'
    TYPE_CHOICES = [
        (TYPE_ARTICLE, 'Article existant'),
        (TYPE_LIBRE, 'Ligne libre'),
    ]

    PRIX_SOURCE_DERNIER_ACHAT = 'DERNIER_ACHAT'
    PRIX_SOURCE_MANUEL = 'MANUEL'
    PRIX_SOURCE_CHOICES = [
        (PRIX_SOURCE_DERNIER_ACHAT, 'Dernier prix d\'achat'),
        (PRIX_SOURCE_MANUEL, 'Saisie manuelle'),
    ]

    requisition = models.ForeignKey(
        Requisition, on_delete=models.CASCADE, related_name='lignes',
    )
    type_ligne = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_ARTICLE)
    article = models.ForeignKey(
        Article,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lignes_requisition',
    )
    designation = models.CharField(max_length=255)
    quantite = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    unite = models.CharField(max_length=100, blank=True, default='')
    # Null = jamais approvisionné → afficher « ..... » côté UI / PDF.
    prix_estime = models.DecimalField(max_digits=14, decimal_places=5, null=True, blank=True)
    prix_source = models.CharField(
        max_length=20, choices=PRIX_SOURCE_CHOICES, default=PRIX_SOURCE_MANUEL,
    )
    remarque = models.TextField(blank=True, default='')
    ordre = models.PositiveIntegerField(default=0)
    statut_stock = models.CharField(max_length=32, blank=True, default='')
    stock_actuel = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    seuil_alerte = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)

    class Meta:
        ordering = ['ordre', 'id']
        indexes = [
            models.Index(fields=['requisition_id', 'ordre']),
            models.Index(fields=['requisition_id', 'article_id']),
        ]

    def __str__(self):
        return f'{self.designation} x{self.quantite}'

    @property
    def prix_manquant(self) -> bool:
        return self.prix_estime is None

    @property
    def montant_ligne(self):
        if self.prix_estime is None:
            return None
        return (self.quantite or Decimal('0')) * self.prix_estime


class RequisitionHistorique(models.Model):
    """Trace des changements importants sur une réquisition."""

    requisition = models.ForeignKey(
        Requisition, on_delete=models.CASCADE, related_name='historique',
    )
    action = models.CharField(max_length=64)
    detail = models.TextField(blank=True, default='')
    ancien_statut = models.CharField(max_length=32, blank=True, default='')
    nouveau_statut = models.CharField(max_length=32, blank=True, default='')
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisitions_historique',
    )
    date_action = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-date_action', '-id']
        indexes = [
            models.Index(fields=['requisition_id', 'date_action']),
        ]

    def __str__(self):
        return f'{self.requisition_id} · {self.action}'


# Compatibilité imports historiques (modèles définis dans l'app ``caisse``).
from caisse.models import (  # noqa: E402, F401
    DetailMouvementCaisse,
    EcartCaisse,
    MouvementCaisse,
    SessionCaisse,
    TypeCaisse,
)

