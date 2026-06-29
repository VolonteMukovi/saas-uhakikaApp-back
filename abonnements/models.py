"""
Modèles SaaS : formules, abonnements, paiements et journal d'activation.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _generer_reference_paiement():
    return str(uuid.uuid4())


class FormuleAbonnement(models.Model):
    """Catalogue des formules (Essai, Starter, Standard, Professionnelle, Entreprise)."""

    CODE_ESSAI = 'essai_gratuit'
    CODE_STARTER = 'starter'
    CODE_STANDARD = 'standard'
    CODE_PROFESSIONNEL = 'professionnel'
    CODE_ENTREPRISE = 'entreprise'

    code = models.SlugField(max_length=40, unique=True)
    nom = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    prix_mensuel = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prix_annuel = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    devise = models.CharField(max_length=3, default='USD')
    duree_essai_jours = models.PositiveIntegerField(
        default=0,
        help_text=_('Durée d\'essai automatique à la création d\'entreprise (0 = pas d\'essai auto).'),
    )
    fonctionnalites = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Drapeaux de fonctionnalités autorisées pour cette formule.'),
    )
    limites = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Limites quantitatives (utilisateurs, succursales, etc.).'),
    )
    est_visible_catalogue = models.BooleanField(
        default=True,
        help_text=_('False pour la formule essai interne.'),
    )
    ordre_affichage = models.PositiveSmallIntegerField(default=0)
    est_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ordre_affichage', 'id']
        verbose_name = _('Formule d\'abonnement')
        verbose_name_plural = _('Formules d\'abonnement')

    def __str__(self):
        return self.nom


class AbonnementEntreprise(models.Model):
    """Abonnement / licence courante ou historique d'une entreprise."""

    STATUT_ESSAI = 'essai'
    STATUT_EN_ATTENTE = 'en_attente'
    STATUT_ACTIF = 'actif'
    STATUT_EXPIRE = 'expire'
    STATUT_SUSPENDU = 'suspendu'
    STATUT_ANNULE = 'annule'

    STATUT_CHOICES = (
        (STATUT_ESSAI, _('Essai gratuit')),
        (STATUT_EN_ATTENTE, _('En attente de validation')),
        (STATUT_ACTIF, _('Actif')),
        (STATUT_EXPIRE, _('Expiré')),
        (STATUT_SUSPENDU, _('Suspendu')),
        (STATUT_ANNULE, _('Annulé')),
    )

    PERIODE_ESSAI = 'essai'
    PERIODE_MENSUEL = 'mensuel'
    PERIODE_ANNUEL = 'annuel'

    PERIODE_CHOICES = (
        (PERIODE_ESSAI, _('Essai')),
        (PERIODE_MENSUEL, _('Mensuel')),
        (PERIODE_ANNUEL, _('Annuel')),
    )

    entreprise = models.ForeignKey(
        'stock.Entreprise',
        on_delete=models.CASCADE,
        related_name='abonnements',
    )
    formule = models.ForeignKey(
        FormuleAbonnement,
        on_delete=models.PROTECT,
        related_name='abonnements',
    )
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_EN_ATTENTE)
    periode = models.CharField(max_length=20, choices=PERIODE_CHOICES, default=PERIODE_MENSUEL)
    date_debut = models.DateTimeField(default=timezone.now)
    date_fin = models.DateTimeField(null=True, blank=True)
    renouvellement_auto = models.BooleanField(default=False)
    activation_manuelle = models.BooleanField(default=False)
    active_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='abonnements_actives',
    )
    notes = models.TextField(blank=True)
    est_courant = models.BooleanField(
        default=False,
        help_text=_('Un seul abonnement courant par entreprise.'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Abonnement entreprise')
        verbose_name_plural = _('Abonnements entreprise')
        indexes = [
            models.Index(fields=['entreprise', 'est_courant']),
            models.Index(fields=['statut', 'date_fin']),
        ]

    def __str__(self):
        return f'{self.entreprise_id} — {self.formule.nom} ({self.statut})'

    @property
    def est_actif(self):
        now = timezone.now()
        if self.statut in (self.STATUT_SUSPENDU, self.STATUT_ANNULE):
            return False
        if self.statut == self.STATUT_EN_ATTENTE:
            return False
        if self.date_fin and self.date_fin < now:
            return False
        return self.statut in (self.STATUT_ESSAI, self.STATUT_ACTIF)

    @property
    def jours_restants(self):
        if not self.date_fin:
            return None
        delta = self.date_fin - timezone.now()
        return max(0, delta.days)


class PaiementAbonnement(models.Model):
    """Paiement lié à un abonnement (manuel ou futur gateway)."""

    STATUT_EN_ATTENTE = 'en_attente'
    STATUT_CONFIRME = 'confirme'
    STATUT_ECHEC = 'echec'
    STATUT_REMBOURSE = 'rembourse'

    STATUT_CHOICES = (
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_CONFIRME, _('Confirmé')),
        (STATUT_ECHEC, _('Échec')),
        (STATUT_REMBOURSE, _('Remboursé')),
    )

    FOURNISSEUR_MANUEL = 'manuel'
    FOURNISSEUR_MAISHAPAY = 'maisha_pay'
    FOURNISSEUR_FLEXPAY = 'flexpay'
    FOURNISSEUR_SERDI = 'serdinate_pay'

    FOURNISSEUR_CHOICES = (
        (FOURNISSEUR_MANUEL, _('Activation manuelle')),
        (FOURNISSEUR_MAISHAPAY, _('Maisha Pay')),
        (FOURNISSEUR_FLEXPAY, _('FlexPay')),
        (FOURNISSEUR_SERDI, _('SerdinatePay')),
    )

    abonnement = models.ForeignKey(
        AbonnementEntreprise,
        on_delete=models.CASCADE,
        related_name='paiements',
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    devise = models.CharField(max_length=3, default='USD')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_EN_ATTENTE)
    fournisseur = models.CharField(max_length=30, choices=FOURNISSEUR_CHOICES, default=FOURNISSEUR_MANUEL)
    reference_interne = models.CharField(
        max_length=64,
        unique=True,
        default=_generer_reference_paiement,
        editable=False,
        help_text=_('Référence unique UHAKIKAAPP transmise au gateway.'),
    )
    reference_externe = models.CharField(max_length=255, blank=True)
    url_paiement = models.URLField(blank=True)
    payload_gateway = models.JSONField(default=dict, blank=True)
    confirme_at = models.DateTimeField(null=True, blank=True)
    confirme_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_abonnement_confirmes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Paiement abonnement')
        verbose_name_plural = _('Paiements abonnement')

    def __str__(self):
        return f'Paiement {self.id} — {self.montant} {self.devise} ({self.statut})'


class JournalWebhookPaiement(models.Model):
    """Traçabilité des notifications reçues des gateways."""

    STATUT_RECU = 'recu'
    STATUT_TRAITE = 'traite'
    STATUT_IGNORE = 'ignore'
    STATUT_ERREUR = 'erreur'

    STATUT_CHOICES = (
        (STATUT_RECU, _('Reçu')),
        (STATUT_TRAITE, _('Traité')),
        (STATUT_IGNORE, _('Ignoré')),
        (STATUT_ERREUR, _('Erreur')),
    )

    fournisseur = models.CharField(max_length=30)
    paiement = models.ForeignKey(
        PaiementAbonnement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='webhooks',
    )
    reference_interne = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict)
    statut_traitement = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_RECU)
    message = models.TextField(blank=True)
    ip_source = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Journal webhook paiement')
        verbose_name_plural = _('Journal webhooks paiement')

    def __str__(self):
        return f'Webhook {self.fournisseur} — {self.statut_traitement}'


class JournalActivationLicence(models.Model):
    """Traçabilité des activations, suspensions et changements de plan."""

    ACTION_ESSAI_DEMARRE = 'essai_demarre'
    ACTION_DEMANDE_ABONNEMENT = 'demande_abonnement'
    ACTION_ACTIVATION_MANUELLE = 'activation_manuelle'
    ACTION_ACTIVATION_PAIEMENT = 'activation_paiement'
    ACTION_EXPIRATION = 'expiration'
    ACTION_SUSPENSION = 'suspension'
    ACTION_REACTIVATION = 'reactivation'
    ACTION_CHANGEMENT_PLAN = 'changement_plan'
    ACTION_PROLONGATION_ESSAI = 'prolongation_essai'

    ACTION_CHOICES = (
        (ACTION_ESSAI_DEMARRE, _('Essai démarré')),
        (ACTION_DEMANDE_ABONNEMENT, _('Demande d\'abonnement')),
        (ACTION_ACTIVATION_MANUELLE, _('Activation manuelle')),
        (ACTION_ACTIVATION_PAIEMENT, _('Activation via paiement')),
        (ACTION_EXPIRATION, _('Expiration')),
        (ACTION_SUSPENSION, _('Suspension')),
        (ACTION_REACTIVATION, _('Réactivation')),
        (ACTION_CHANGEMENT_PLAN, _('Changement de plan')),
        (ACTION_PROLONGATION_ESSAI, _('Prolongation essai')),
    )

    entreprise = models.ForeignKey(
        'stock.Entreprise',
        on_delete=models.CASCADE,
        related_name='journal_licences',
    )
    abonnement = models.ForeignKey(
        AbonnementEntreprise,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='journal',
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    effectue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_licence',
    )
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Journal activation licence')
        verbose_name_plural = _('Journal activations licence')

    def __str__(self):
        return f'{self.entreprise_id} — {self.action}'


class DemandeInstallationPrivee(models.Model):
    """Demande exceptionnelle d'installation locale / privée."""

    STATUT_NOUVELLE = 'nouvelle'
    STATUT_EN_COURS = 'en_cours'
    STATUT_CLOTUREE = 'cloturee'
    STATUT_REFUSEE = 'refusee'

    STATUT_CHOICES = (
        (STATUT_NOUVELLE, _('Nouvelle')),
        (STATUT_EN_COURS, _('En cours d\'étude')),
        (STATUT_CLOTUREE, _('Clôturée')),
        (STATUT_REFUSEE, _('Refusée')),
    )

    entreprise = models.ForeignKey(
        'stock.Entreprise',
        on_delete=models.CASCADE,
        related_name='demandes_installation_privee',
        null=True,
        blank=True,
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demandes_installation_privee',
    )
    nom_contact = models.CharField(max_length=200)
    email_contact = models.EmailField()
    telephone = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=STATUT_NOUVELLE)
    notes_internes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Demande installation privée')
        verbose_name_plural = _('Demandes installation privée')

    def __str__(self):
        return f'Demande privée — {self.nom_contact}'
