from django.db import models
from django.conf import settings
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

    def __str__(self):
        return self.nom


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
        if not self.article_id:
            type_code = self.sous_type_article.type_article.libelle[:2].upper()
            sous_type_code = self.sous_type_article.libelle[:2].upper()
            qs = Article.objects.filter(sous_type_article=self.sous_type_article)
            if self.entreprise_id:
                qs = qs.filter(entreprise_id=self.entreprise_id)
            count = qs.count() + 1
            numero = str(count).zfill(4)
            self.article_id = f"{type_code}{sous_type_code}{numero}"
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
    quantite = models.PositiveIntegerField()
    quantite_restante = models.PositiveIntegerField(default=0, help_text="Quantité encore disponible dans ce lot (FIFO)")
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix d'achat unitaire")
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix de vente unitaire défini à l'entrée")
    date_expiration = models.DateField(null=True, blank=True, help_text="Date d'expiration du produit (optionnelle)")
    date_entree = models.DateTimeField(auto_now_add=True)
    entree = models.ForeignKey(Entree, related_name='lignes', on_delete=models.CASCADE)
    # Devise de la ligne (nullable)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='ligneentrees', null=True, blank=True)
    # Seuil d'alerte obligatoire pour chaque ligne d'entrée
    seuil_alerte = models.PositiveIntegerField(help_text="Seuil d'alerte pour cet article",default=0)

    class Meta:
        ordering = ['date_entree', 'id']  # FIFO : plus ancien en premier
        indexes = [
            models.Index(fields=['article', 'date_entree']),  # Pour requêtes FIFO rapides
        ]

    def __str__(self):
        return f"LigneEntree: {self.article.nom_scientifique} x {self.quantite_restante}/{self.quantite} (Entree {self.entree.id})"
    
    def save(self, *args, **kwargs):
        # Initialiser quantite_restante à quantite si c'est une nouvelle entrée
        if self.pk is None:
            self.quantite_restante = self.quantite
        super().save(*args, **kwargs)



class Stock(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE)
    Qte = models.PositiveIntegerField(default=0)
    seuilAlert = models.PositiveIntegerField(default=0)


    def __str__(self):
        return f"Stock de {self.article.nom_scientifique}"


# Sortie et LigneSortie
class Sortie(models.Model):
    motif = models.CharField(max_length=255, blank=True)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, related_name='sorties', null=True, blank=True, help_text="Client associé à cette sortie (optionnel)")
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='sorties', null=True, blank=True)
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
    is_special = models.BooleanField(
        default=False,
        verbose_name='Client spécial',
        help_text='Si vrai, client priorisé dans les rapports (ex. dettes) par défaut.',
    )
    date_enregistrement = models.DateTimeField(auto_now_add=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='clients', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='clients', null=True, blank=True)

    class Meta:
        ordering = ['nom']
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['succursale_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
            models.Index(fields=['entreprise_id', 'is_special']),
        ]

    def __str__(self):
        return f"{self.id} - {self.nom}"

class DetteClient(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='dettes')
    sortie = models.OneToOneField('Sortie', on_delete=models.CASCADE, related_name='dette')
    montant_total = models.DecimalField(max_digits=12, decimal_places=2)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    solde_restant = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='dettes', null=True, blank=True)
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
        # Définir la date d'échéance par défaut si non fournie (1 mois après création)
        if not self.date_echeance:
            from datetime import timedelta
            self.date_echeance = timezone.now().date() + timedelta(days=30)
        
        # Recalcul automatique du solde et du statut
        self.solde_restant = self.montant_total - self.montant_paye
        if self.solde_restant <= 0:
            self.statut = 'PAYEE'
        else:
            # Vérifie si la date d'échéance est dépassée
            if self.date_echeance and self.date_echeance < timezone.now().date():
                self.statut = 'RETARD'
            else:
                self.statut = 'EN_COURS'
        super().save(*args, **kwargs)



class PaiementDette(models.Model):
    dette = models.ForeignKey(DetteClient, on_delete=models.CASCADE, related_name='paiements')
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2)
    date_paiement = models.DateTimeField(auto_now_add=True)
    moyen = models.CharField(max_length=50, blank=True, null=True, help_text="Ex: Cash, Mobile Money, Chèque")
    reference = models.CharField(max_length=100, blank=True, null=True)
    utilisateur = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_dettes_effectues')
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='paiements_dettes', null=True, blank=True)
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='paiements_dettes', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='paiements_dettes', null=True, blank=True)

    class Meta:
        ordering = ['-date_paiement']
        verbose_name = "Paiement de dette"
        verbose_name_plural = "Paiements de dettes"
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        return f"Paiement {self.montant_paye}{self.devise.sigle if self.devise else ''} - Dette #{self.dette.id}"

    def save(self, *args, **kwargs):
        # Check if this is a new paiement to avoid duplicate updates on subsequent saves
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Only update dette and create mouvement on first save
            # Use update() to avoid triggering dette.save() which could cause recursion
            from django.db.models import F
            DetteClient.objects.filter(pk=self.dette.pk).update(
                montant_paye=F('montant_paye') + self.montant_paye
            )
            # Refresh dette instance to get updated values
            self.dette.refresh_from_db()
            # Recalculate solde and status
            self.dette.solde_restant = self.dette.montant_total - self.dette.montant_paye
            if self.dette.solde_restant <= 0:
                self.dette.statut = 'PAYEE'
            else:
                if self.dette.date_echeance and self.dette.date_echeance < timezone.now().date():
                    self.dette.statut = 'RETARD'
                else:
                    self.dette.statut = 'EN_COURS'
            # Save dette with update_fields to avoid full save() logic
            self.dette.save(update_fields=['solde_restant', 'statut'])

            # Enregistrer automatiquement le mouvement de caisse (même entreprise/succursale que la dette)
            from .models import MouvementCaisse
            MouvementCaisse.objects.create(
                type='ENTREE',
                montant=self.montant_paye,
                devise=self.devise or self.dette.devise,
                motif=f"Paiement dette client {self.dette.client.nom}",
                moyen=self.moyen or "Inconnu",
                reference_piece=f"DET-{self.dette.id}",
                entreprise_id=self.dette.entreprise_id,
                succursale_id=self.dette.succursale_id,
            )




class LigneSortie(models.Model):
    
    sortie = models.ForeignKey(Sortie, related_name='lignes', on_delete=models.CASCADE)
    article = models.ForeignKey(Article, related_name='sorties', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Prix réellement encaissé (peut différer du prix de vente du lot en cas de promotion/réduction)")
    date_sortie = models.DateTimeField(auto_now_add=True)
    # Devise de la ligne de sortie (nullable)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='lignesorties', null=True, blank=True)

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
    quantite = models.PositiveIntegerField(help_text="Quantité prélevée de ce lot")
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix d'achat du lot (copié)")
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix de vente du lot (copié)")
    
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
    quantite_vendue = models.PositiveIntegerField()
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2)
    benefice_unitaire = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix vente - Prix achat")
    benefice_total = models.DecimalField(max_digits=12, decimal_places=2, help_text="Bénéfice total pour cette quantité")
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

# Ajout du modèle de suivi des bénéfices par vente

class MouvementCaisse(models.Model):
    TYPE_CHOICES = [('ENTREE', 'Entrée'), ('SORTIE', 'Sortie')]
    date = models.DateTimeField(auto_now_add=True)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    devise = models.ForeignKey('Devise', on_delete=models.CASCADE, related_name='mouvements_caisse', null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    motif = models.TextField()
    moyen = models.CharField(max_length=30, blank=True, null=True, help_text='Ex: Cash, Mobile Money, Chèque')
    reference_piece = models.CharField(max_length=100, blank=True, null=True)
    sortie = models.ForeignKey('Sortie', null=True, blank=True, on_delete=models.SET_NULL, related_name='mouvement_caisse')
    entree = models.ForeignKey('Entree', null=True, blank=True, on_delete=models.SET_NULL, related_name='mouvement_caisse')
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='mouvements_caisse', null=True, blank=True)
    succursale = models.ForeignKey(Succursale, on_delete=models.CASCADE, related_name='mouvements_caisse', null=True, blank=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['succursale_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
        ]

    def __str__(self):
        sens = '+' if self.type == 'ENTREE' else '-'
        return f"{self.date.strftime('%Y-%m-%d %H:%M')} {sens}{self.montant} ({self.motif[:20]}...)"

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
       
                est_principal=True
            ).exists()
            
            # Si aucune devise principale n'existe, forcer celle-ci à être principale
            if not has_principal:
                self.est_principal = True
        
        # Si cette devise devient principale, désactiver les autres
        if self.est_principal:
            Devise.objects.filter(
   
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
       
                        est_principal=True
                    ).exclude(pk=self.pk).exists()
                    
                    if not autres_principales:
                        # Promouvoir automatiquement une autre devise
                        autre_devise = Devise.objects.filter(
                  
                        ).exclude(pk=self.pk).first()
                        
                        if autre_devise:
                            autre_devise.est_principal = True
                            autre_devise.save()
        
        super().save(*args, **kwargs)

    def __str__(self):
        principal_str = " [PRINCIPALE]" if self.est_principal else ""
        return f"{self.nom} ({self.sigle}){principal_str} - {self.entreprise.nom}"




