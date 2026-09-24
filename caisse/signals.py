"""
Signaux caisse : caisse par défaut à la création entreprise / succursale,
synchronisation statut dette après paiement.
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from caisse.models import MouvementCaisse
from caisse.services.caisse_defaut import ensure_caisse_defaut_entreprise, ensure_caisse_defaut_succursale
from stock.models import DetteClient, Entreprise, Succursale
from stock.services.dette_statut import appliquer_statut_dette


@receiver(post_save, sender=MouvementCaisse)
def sync_dette_apres_mouvement_caisse(sender, instance, **kwargs):
    if instance.type != 'ENTREE':
        return
    if not instance.content_type_id or not instance.object_id:
        return
    model = instance.content_type.model_class()
    if model is not DetteClient:
        return
    transaction.on_commit(lambda did=instance.object_id: appliquer_statut_dette(did))


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
