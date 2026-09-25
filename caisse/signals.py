"""
Signaux caisse : caisse par défaut à la création entreprise / succursale.
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from caisse.services.caisse_defaut import ensure_caisse_defaut_entreprise, ensure_caisse_defaut_succursale
from stock.models import Entreprise, Succursale


@receiver(post_save, sender=Entreprise)
def creer_caisse_defaut_entreprise(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: ensure_caisse_defaut_entreprise(instance.pk))


@receiver(post_save, sender=Succursale)
def creer_caisse_defaut_succursale(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: ensure_caisse_defaut_succursale(instance))
