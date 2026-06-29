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
