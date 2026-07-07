"""
Modèles inscription plateforme (connexion sociale préparée pour étape suivante).
"""
from django.conf import settings
from django.db import models


class ProfilConnexionGoogle(models.Model):
    """Liaison compte Google ↔ utilisateur UHAKIKAAPP (OAuth — étape 2)."""

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profil_google',
    )
    google_sub = models.CharField(max_length=255, unique=True)
    email_google = models.EmailField(blank=True)
    avatar_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil connexion Google'
        verbose_name_plural = 'Profils connexion Google'

    def __str__(self):
        return f'Google {self.google_sub} → {self.utilisateur_id}'


class EmailVerificationToken(models.Model):
    """Jeton de confirmation d'adresse e-mail (usage unique, durée limitée)."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jetons_verification_email',
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    email_cible = models.EmailField(
        help_text='Adresse visée au moment de la génération (utile si changement en attente).',
    )
    cree_le = models.DateTimeField(auto_now_add=True)
    expire_le = models.DateTimeField()
    utilise_le = models.DateTimeField(null=True, blank=True)
    invalide = models.BooleanField(default=False)

    class Meta:
        ordering = ['-cree_le']
        indexes = [
            models.Index(fields=['utilisateur', '-cree_le']),
            models.Index(fields=['expire_le']),
        ]
        verbose_name = 'Jeton vérification e-mail'
        verbose_name_plural = 'Jetons vérification e-mail'

    def __str__(self):
        return f'Verif email user={self.utilisateur_id} ({self.email_cible})'


class WorkspaceActivationToken(models.Model):
    """Jeton d'activation finale de l'espace (post-onboarding, lien e-mail bienvenue)."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='jetons_activation_espace',
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    expire_le = models.DateTimeField()
    utilise_le = models.DateTimeField(null=True, blank=True)
    invalide = models.BooleanField(default=False)

    class Meta:
        ordering = ['-cree_le']
        indexes = [
            models.Index(fields=['utilisateur', '-cree_le']),
            models.Index(fields=['expire_le']),
        ]
        verbose_name = 'Jeton activation espace'
        verbose_name_plural = 'Jetons activation espace'

    def __str__(self):
        return f'Activation espace user={self.utilisateur_id}'


class EmailEnvoiLog(models.Model):
    """Journal des envois e-mail transactionnels (diagnostic / anti-doublon)."""

    TYPE_VERIFICATION = 'verification_email'
    TYPE_BIENVENUE = 'welcome_email'
    TYPE_ACTIVATION_ESPACE = 'workspace_activation'

    STATUT_PREPARE = 'prepare'
    STATUT_ENVOYE = 'envoye'
    STATUT_ECHEC = 'echec'

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='journal_emails',
        null=True,
        blank=True,
    )
    type_email = models.CharField(max_length=32, db_index=True)
    destinataire = models.EmailField()
    sujet = models.CharField(max_length=255, blank=True)
    statut = models.CharField(max_length=20, default=STATUT_PREPARE, db_index=True)
    code_erreur = models.CharField(max_length=64, blank=True)
    details = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    envoye_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-cree_le']
        indexes = [
            models.Index(fields=['utilisateur', 'type_email', '-cree_le']),
            models.Index(fields=['destinataire', 'type_email', '-cree_le']),
        ]
        verbose_name = 'Journal envoi e-mail'
        verbose_name_plural = 'Journal envois e-mail'

    def __str__(self):
        return f'{self.type_email} → {self.destinataire} ({self.statut})'
