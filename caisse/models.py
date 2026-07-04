from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from caisse.constants import CAISSE_DEFAUT_CODE, CAISSE_DEFAUT_LIBELLE, CAISSE_DEFAUT_NOM, CODE_TYPE_CAISSE_CHOICES


class TypeCaisse(models.Model):
    """
    Caisse (canal de réception / sortie d'argent) : cash, banque, mobile money, etc.
    Le nom de modèle historique ``TypeCaisse`` est conservé pour compatibilité base/API.
    """

    nom = models.CharField(max_length=120, blank=True, default='')
    libelle = models.CharField(max_length=120)
    code_type = models.CharField(
        max_length=20,
        choices=CODE_TYPE_CAISSE_CHOICES,
        default=CAISSE_DEFAUT_CODE,
        help_text='Catégorie de caisse (CASH, BANQUE, AIRTEL_MONEY, …).',
    )
    description = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='types_caisse/', blank=True, null=True)
    entreprise = models.ForeignKey(
        'stock.Entreprise', on_delete=models.CASCADE, related_name='types_caisse',
    )
    succursale = models.ForeignKey(
        'stock.Succursale', on_delete=models.CASCADE, null=True, blank=True, related_name='types_caisse',
    )
    devise = models.ForeignKey(
        'stock.Devise',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='caisses',
        help_text='Devise principale de cette caisse.',
    )
    is_active = models.BooleanField(default=True)
    est_defaut = models.BooleanField(
        default=False,
        help_text='Caisse cash physique par défaut pour l\'entreprise / agence.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_typecaisse'
        ordering = ['entreprise_id', 'nom', 'libelle']
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
            models.Index(fields=['entreprise_id', 'est_defaut']),
            models.Index(fields=['entreprise_id', 'code_type']),
        ]
        verbose_name = 'Caisse'
        verbose_name_plural = 'Caisses'

    def __str__(self):
        return self.nom or self.libelle

    def save(self, *args, **kwargs):
        if not (self.nom or '').strip():
            self.nom = (self.libelle or CAISSE_DEFAUT_NOM).strip()
        if not (self.libelle or '').strip():
            self.libelle = self.nom
        super().save(*args, **kwargs)

    @property
    def libelle_affiche(self) -> str:
        return self.libelle or self.nom

class SessionCaisse(models.Model):
    """Session de caisse : période d'activité financière entre ouverture et clôture."""

    STATUT_CHOICES = [
        ('OUVERTE', 'Ouverte'),
        ('CLOTUREE_EN_ATTENTE_VALIDATION', 'Clôturée en attente validation écart'),
        ('CLOTUREE', 'Clôturée'),
        ('ANNULEE', 'Annulée'),
    ]

    numero = models.CharField(max_length=40, unique=True)
    type_caisse = models.ForeignKey(
        TypeCaisse, on_delete=models.PROTECT, related_name='sessions_caisse',
    )
    devise = models.ForeignKey('stock.Devise', on_delete=models.PROTECT, related_name='sessions_caisse')
    entreprise = models.ForeignKey(
        'stock.Entreprise', on_delete=models.CASCADE, related_name='sessions_caisse',
    )
    succursale = models.ForeignKey(
        'stock.Succursale', on_delete=models.CASCADE, null=True, blank=True, related_name='sessions_caisse',
    )
    ouvert_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions_caisse_ouvertes',
    )
    cloture_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions_caisse_cloturees',
    )
    ouvert_le = models.DateTimeField()
    cloture_le = models.DateTimeField(null=True, blank=True)
    solde_ouverture = models.DecimalField(max_digits=14, decimal_places=5, default=Decimal('0'))
    total_entrees = models.DecimalField(max_digits=14, decimal_places=5, default=Decimal('0'))
    total_sorties = models.DecimalField(max_digits=14, decimal_places=5, default=Decimal('0'))
    solde_theorique = models.DecimalField(max_digits=14, decimal_places=5, null=True, blank=True)
    montant_physique = models.DecimalField(max_digits=14, decimal_places=5, null=True, blank=True)
    ecart_montant = models.DecimalField(max_digits=14, decimal_places=5, null=True, blank=True)
    statut = models.CharField(max_length=40, choices=STATUT_CHOICES, default='OUVERTE')
    commentaire_cloture = models.TextField(blank=True, default='')
    est_legacy = models.BooleanField(
        default=False,
        help_text="Session créée par migration pour rattacher l'historique existant.",
    )

    class Meta:
        db_table = 'stock_sessioncaisse'
        ordering = ['-ouvert_le', '-id']
        indexes = [
            models.Index(fields=['entreprise_id', 'succursale_id', 'statut']),
            models.Index(fields=['type_caisse_id', 'devise_id', 'statut']),
        ]
        verbose_name = 'Session de caisse'
        verbose_name_plural = 'Sessions de caisse'

    def __str__(self):
        return f"{self.numero} ({self.get_statut_display()})"


class MouvementCaisse(models.Model):
    TYPE_CHOICES = [('ENTREE', 'Entrée'), ('SORTIE', 'Sortie')]
    CATEGORIE_CHOICES = [
        ('VENTE', 'Vente comptant'),
        ('PAIEMENT_DETTE', 'Paiement dette client'),
        ('APPROVISIONNEMENT', 'Approvisionnement payé cash'),
        ('DEPENSE', 'Dépense'),
        ('ENTREE_MANUELLE', 'Entrée manuelle'),
        ('SORTIE_MANUELLE', 'Sortie manuelle'),
        ('AJUSTEMENT_SURPLUS_CAISSE', 'Ajustement surplus caisse'),
        ('AJUSTEMENT_PERTE_CAISSE', 'Ajustement perte caisse'),
        ('AUTRE', 'Autre'),
    ]
    date = models.DateTimeField(auto_now_add=True)
    montant = models.DecimalField(max_digits=12, decimal_places=5)
    devise = models.ForeignKey(
        'stock.Devise', on_delete=models.CASCADE, related_name='mouvements_caisse', null=True, blank=True,
    )
    devise_reference = models.ForeignKey(
        'stock.Devise',
        on_delete=models.PROTECT,
        related_name='mouvements_caisse_reference',
        null=True,
        blank=True,
    )
    taux_change = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    montant_reference = models.DecimalField(max_digits=14, decimal_places=5, default=Decimal('0'))
    montant_origine = models.DecimalField(
        max_digits=14, decimal_places=5, null=True, blank=True,
        help_text='Montant d\'origine avant conversion vers la devise de la caisse.',
    )
    devise_origine = models.ForeignKey(
        'stock.Devise',
        on_delete=models.PROTECT,
        related_name='mouvements_caisse_origine',
        null=True,
        blank=True,
    )
    taux_conversion = models.DecimalField(
        max_digits=20, decimal_places=8, null=True, blank=True,
        help_text='Taux appliqué : 1 unité devise_origine = taux_conversion unités devise caisse.',
    )
    date_taux = models.DateTimeField(null=True, blank=True, help_text='Date du taux utilisé pour la conversion caisse.')
    montant_applique = models.DecimalField(
        max_digits=14, decimal_places=5, null=True, blank=True,
        help_text='Montant imputé sur l\'objet lié (ex. dette) dans la devise métier de cet objet.',
    )
    devise_applique = models.ForeignKey(
        'stock.Devise',
        on_delete=models.PROTECT,
        related_name='mouvements_caisse_applique',
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    motif = models.TextField(blank=True, default='', help_text='Libellé / motif du mouvement.')
    moyen = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text='Ex. : Cash, Mobile Money, Chèque (optionnel).',
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mouvements_caisse_effectues',
    )
    reference_piece = models.CharField(max_length=100, blank=True, default='')
    sortie = models.ForeignKey(
        'stock.Sortie', null=True, blank=True, on_delete=models.SET_NULL, related_name='mouvement_caisse',
    )
    entree = models.ForeignKey(
        'stock.Entree', null=True, blank=True, on_delete=models.SET_NULL, related_name='mouvement_caisse',
    )
    entreprise = models.ForeignKey(
        'stock.Entreprise', on_delete=models.CASCADE, related_name='mouvements_caisse', null=True, blank=True,
    )
    succursale = models.ForeignKey(
        'stock.Succursale', on_delete=models.CASCADE, related_name='mouvements_caisse', null=True, blank=True,
    )
    session_caisse = models.ForeignKey(
        SessionCaisse,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='mouvements',
    )
    type_caisse = models.ForeignKey(
        TypeCaisse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mouvements',
    )
    categorie = models.CharField(max_length=40, choices=CATEGORIE_CHOICES, blank=True, default='AUTRE')

    class Meta:
        db_table = 'stock_mouvementcaisse'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['entreprise_id']),
            models.Index(fields=['succursale_id']),
            models.Index(fields=['entreprise_id', 'succursale_id']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['session_caisse_id', 'date']),
        ]

    def __str__(self):
        sens = '+' if self.type == 'ENTREE' else '-'
        return f"{self.date.strftime('%Y-%m-%d %H:%M')} {sens}{self.montant}"

    def motif_affiche(self) -> str:
        from caisse.services.caisse import motif_mouvement_concatene
        return motif_mouvement_concatene(self)


class DetailMouvementCaisse(models.Model):
    """Ventilation d'un mouvement sur plusieurs types de caisse."""

    mouvement = models.ForeignKey(MouvementCaisse, on_delete=models.CASCADE, related_name='details')
    type_caisse = models.ForeignKey(
        TypeCaisse, on_delete=models.SET_NULL, null=True, blank=True, related_name='details_mouvements',
    )
    montant = models.DecimalField(max_digits=12, decimal_places=5)
    motif_explicite = models.TextField(
        blank=True, default='', help_text="Si pas de type_caisse, motif obligatoire ou généré automatiquement.",
    )
    reference_piece = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        db_table = 'stock_detailmouvementcaisse'
        ordering = ['id']
        verbose_name = 'Détail mouvement caisse'
        verbose_name_plural = 'Détails mouvements caisse'

    def __str__(self):
        return f"{self.montant} ({self.type_caisse or 'sans type'})"


class EcartCaisse(models.Model):
    """Écart constaté à la clôture d'une session (surplus ou perte)."""

    TYPE_ECART_CHOICES = [
        ('SURPLUS', 'Surplus'),
        ('PERTE', 'Perte'),
    ]
    STATUT_CHOICES = [
        ('EN_ATTENTE_VALIDATION', 'En attente validation'),
        ('VALIDE', 'Validé'),
        ('REJETE', 'Rejeté'),
        ('ANNULE', 'Annulé'),
    ]

    session = models.OneToOneField(SessionCaisse, on_delete=models.CASCADE, related_name='ecart')
    type_ecart = models.CharField(max_length=10, choices=TYPE_ECART_CHOICES)
    montant = models.DecimalField(max_digits=14, decimal_places=5, help_text="Montant absolu de l'écart")
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='EN_ATTENTE_VALIDATION')
    declare_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecarts_caisse_declares',
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecarts_caisse_valides',
    )
    valide_le = models.DateTimeField(null=True, blank=True)
    commentaire = models.TextField(blank=True, default='')
    mouvement_ajustement = models.ForeignKey(
        MouvementCaisse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ecart_source',
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_ecartcaisse'
        ordering = ['-cree_le']
        verbose_name = 'Écart de caisse'
        verbose_name_plural = 'Écarts de caisse'

    def __str__(self):
        return f"{self.get_type_ecart_display()} {self.montant} — {self.get_statut_display()}"
