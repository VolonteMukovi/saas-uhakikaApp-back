"""
Signaux : synchronisation du statut de dette après enregistrement d'un mouvement de caisse
lié à une DetteClient (content_type / object_id, entrée de caisse).
"""
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from stock.models import DetteClient, MouvementCaisse


def _maj_statut_dette(dette_id: int) -> None:
    dette = DetteClient.objects.filter(pk=dette_id).first()
    if not dette:
        return
    solde = dette.solde_restant
    today = timezone.now().date()
    if solde <= 0:
        statut = 'PAYEE'
    elif dette.date_echeance and dette.date_echeance < today:
        statut = 'RETARD'
    else:
        statut = 'EN_COURS'
    DetteClient.objects.filter(pk=dette_id).update(statut=statut)


@receiver(post_save, sender=MouvementCaisse)
def sync_dette_apres_mouvement_caisse(sender, instance, **kwargs):
    if instance.type != 'ENTREE':
        return
    if not instance.content_type_id or not instance.object_id:
        return
    model = instance.content_type.model_class()
    if model is not DetteClient:
        return
    transaction.on_commit(lambda did=instance.object_id: _maj_statut_dette(did))
