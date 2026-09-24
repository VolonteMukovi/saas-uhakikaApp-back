"""Recalcule les statuts des dettes (PAYEE si solde <= 0, même avant échéance)."""
from django.core.management.base import BaseCommand

from stock.services.dette_statut import sync_statuts_dettes


class Command(BaseCommand):
    help = (
        "Recalcule DetteClient.statut : solde <= 0 → PAYEE "
        "(paiement anticipé inclus), sinon RETARD / EN_COURS."
    )

    def add_arguments(self, parser):
        parser.add_argument('--entreprise-id', type=int, default=None)
        parser.add_argument('--succursale-id', type=int, default=None)

    def handle(self, *args, **options):
        counts = sync_statuts_dettes(
            entreprise_id=options['entreprise_id'],
            succursale_id=options['succursale_id'],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Scan {counts['scannees']} | mises à jour {counts['mises_a_jour']} | "
                f"PAYEE={counts['payees']} EN_COURS={counts['en_cours']} RETARD={counts['retard']}"
            )
        )
