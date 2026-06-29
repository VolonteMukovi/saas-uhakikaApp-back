"""Signal : essai gratuit automatique à la création d'une entreprise."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from abonnements.services.licence import demarrer_essai_gratuit


@receiver(post_save, sender='stock.Entreprise')
def creer_essai_gratuit_entreprise(sender, instance, created, **kwargs):
    if created:
        demarrer_essai_gratuit(instance)
