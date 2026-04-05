from django.conf import settings
from django.db import models
from django.utils.translation import gettext as _


class Fournisseur(models.Model):
    """
    Fournisseur (achats / approvisionnement), isolé par entreprise (SaaS).
    Indexation pour listes et jointures fréquentes avec les lots en transit.
    """

    entreprise = models.ForeignKey(
        "stock.Entreprise",
        on_delete=models.CASCADE,
        related_name="fournisseurs",
    )
    succursale = models.ForeignKey(
        "stock.Succursale",
        on_delete=models.CASCADE,
        related_name="fournisseurs",
        null=True,
        blank=True,
    )
    code = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Code interne unique par entreprise (généré automatiquement si vide).",
    )
    nom = models.CharField(max_length=255)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    ville = models.CharField(max_length=100, blank=True, null=True)
    pays = models.CharField(max_length=100, blank=True, null=True)
    nif = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("entreprise", "code")
        ordering = ["nom", "id"]
        indexes = [
            models.Index(fields=["entreprise_id", "nom"]),
            models.Index(fields=["entreprise_id", "is_active"]),
            models.Index(fields=["entreprise_id", "code"]),
            models.Index(fields=["entreprise_id", "created_at"]),
        ]
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"

    def __str__(self) -> str:
        return f"{self.code} — {self.nom}"

    def save(self, *args, **kwargs):
        if self.entreprise_id and (not self.code or not str(self.code).strip()):
            n = (
                Fournisseur.objects.filter(entreprise_id=self.entreprise_id)
                .exclude(pk=self.pk)
                .count()
                + 1
            )
            self.code = f"FOU{n:06d}"
        super().save(*args, **kwargs)


class Lot(models.Model):
    """
    Lot de marchandises en cours de transport.

    Référencé (reference) et suivi en multi-tenant via `entreprise` / `succursale`.
    """

    class StatutLot(models.TextChoices):
        EN_TRANSIT = "EN_TRANSIT", _("En transit")
        ARRIVE = "ARRIVE", _("Arrivé")
        CLOTURE = "CLOTURE", _("Clôturé")

    entreprise = models.ForeignKey(
        "stock.Entreprise",
        on_delete=models.CASCADE,
        related_name="lots_en_transit",
    )
    succursale = models.ForeignKey(
        "stock.Succursale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lots_en_transit",
    )

    # Identifiant humain unique (par entreprise)
    reference = models.CharField(max_length=30)

    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.SET_NULL,
        related_name="lots_en_transit",
        null=True,
        blank=True,
    )

    date_expedition = models.DateField(help_text="Date d'expédition du lot.")
    date_arrivee_prevue = models.DateField(
        null=True,
        blank=True,
        help_text="Date d'arrivée prévue (optionnelle).",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutLot.choices,
        default=StatutLot.EN_TRANSIT,
    )
    date_cloture = models.DateField(
        null=True,
        blank=True,
        help_text="Date de clôture (optionnelle).",
    )
    entree_stock = models.ForeignKey(
        "stock.Entree",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lots_transit_origine",
        help_text="Entrée de stock générée à la clôture (tracabilité, pas d'entrée avant clôture).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("entreprise", "reference")
        indexes = [
            models.Index(fields=["entreprise", "statut"]),
            models.Index(fields=["entreprise", "fournisseur"]),
            models.Index(fields=["entreprise", "date_expedition"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Lot {self.reference} ({self.get_statut_display()})"


class FraisLot(models.Model):
    """Frais associés à un lot (transport, douane, manutention...)."""

    class TypeFrais(models.TextChoices):
        TRANSPORT = "TRANSPORT", _("Transport")
        DOUANE = "DOUANE", _("Douane")
        MANUTENTION = "MANUTENTION", _("Manutention")

    entreprise = models.ForeignKey(
        "stock.Entreprise",
        on_delete=models.CASCADE,
        related_name="frais_lots",
    )
    succursale = models.ForeignKey(
        "stock.Succursale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="frais_lots",
    )

    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="frais")
    type_frais = models.CharField(max_length=20, choices=TypeFrais.choices)
    montant = models.DecimalField(max_digits=14, decimal_places=2)
    devise = models.ForeignKey("stock.Devise", on_delete=models.PROTECT, related_name="frais_lots")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["entreprise", "lot", "type_frais"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_type_frais_display()} - {self.montant} {getattr(self.devise, 'sigle', '')}"


class LotItem(models.Model):
    """Détail des articles inclus dans un lot."""

    entreprise = models.ForeignKey(
        "stock.Entreprise",
        on_delete=models.CASCADE,
        related_name="lot_items",
    )
    succursale = models.ForeignKey(
        "stock.Succursale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lot_items",
    )

    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="items")
    article = models.ForeignKey("stock.Article", on_delete=models.PROTECT, related_name="lot_items")

    quantite = models.PositiveIntegerField()
    prix_achat_unitaire = models.DecimalField(max_digits=14, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("lot", "article")
        indexes = [
            models.Index(fields=["entreprise", "lot", "article"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.article} x {self.quantite} (lot {self.lot.reference})"


class Commande(models.Model):
    """Commande client (livraison ultérieure)."""

    class StatutCommande(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", _("En attente")
        ACCEPTEE = "ACCEPTEE", _("Acceptée")
        LIVREE = "LIVREE", _("Livrée")
        REJETEE = "REJETEE", _("Rejetée")

    client = models.ForeignKey(
        "stock.Client",
        on_delete=models.CASCADE,
        related_name="commandes",
    )
    entreprise = models.ForeignKey(
        "stock.Entreprise",
        on_delete=models.CASCADE,
        related_name="commandes",
    )
    succursale = models.ForeignKey(
        "stock.Succursale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commandes",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutCommande.choices,
        default=StatutCommande.EN_ATTENTE,
        db_index=True,
    )
    reference = models.CharField(
        max_length=40,
        blank=True,
        default="",
        db_index=True,
        help_text="Référence affichée (générée si vide).",
    )
    nom = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Libellé optionnel (ex. désignation provisoire si le catalogue n’est pas à jour).",
    )
    note_client = models.TextField(blank=True, default="", help_text="Message ou instructions du client.")
    sortie_livraison = models.OneToOneField(
        "stock.Sortie",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commande_livraison",
        help_text="Sortie de stock créée automatiquement lors du passage au statut « livrée ».",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["entreprise_id", "client_id", "statut"]),
            models.Index(fields=["entreprise_id", "created_at"]),
            models.Index(fields=["entreprise_id", "statut", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Commande {self.reference or self.pk} ({self.get_statut_display()})"

    def save(self, *args, **kwargs):
        first = self.pk is None
        super().save(*args, **kwargs)
        if first and not (self.reference and str(self.reference).strip()):
            ref = f"CMD-{self.entreprise_id}-{self.pk:06d}"
            Commande.objects.filter(pk=self.pk).update(reference=ref)
            self.reference = ref


class CommandeItem(models.Model):
    """Ligne de commande : article catalogue OU désignation libre (exclusivement)."""

    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name="items",
    )
    article = models.ForeignKey(
        "stock.Article",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="commande_items",
    )
    nom_article = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Produit non référencé au catalogue (si pas d’article_id).",
    )
    quantite = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["commande_id", "article_id"]),
        ]

    def __str__(self) -> str:
        if self.article_id:
            return f"{self.article_id} x {self.quantite}"
        return f"{self.nom_article} x {self.quantite}"


class CommandeResponse(models.Model):
    """Suivi / validation / retour sur une commande (équipe interne ou processus métier)."""

    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name="reponses",
    )
    commentaire = models.TextField(help_text="Commentaire de suivi, validation ou retour.")
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commande_reponses",
        help_text="Utilisateur interne ayant saisi la réponse (admin / staff).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["commande_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Réponse commande #{self.commande_id}"

