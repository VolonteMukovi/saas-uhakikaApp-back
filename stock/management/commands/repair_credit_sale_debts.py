"""Répare les ventes à crédit sans DetteClient + aligne les dates dette ← vente."""
from django.core.management.base import BaseCommand
from django.db import transaction

from stock.services.credit_sale_debt import (
    create_dette_for_credit_sortie,
    find_credit_sorties_without_dette,
    sync_dette_dates_from_sorties,
)


class Command(BaseCommand):
    help = (
        "Crée les dettes manquantes pour les sorties EN_CREDIT, "
        "et aligne DetteClient.date_creation sur la date de vente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--entreprise-id',
            type=int,
            default=None,
            help='Limiter à une entreprise (ID).',
        )
        parser.add_argument(
            '--succursale-id',
            type=int,
            default=None,
            help='Limiter à une succursale (ID).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Afficher les sorties concernées sans créer les dettes.',
        )
        parser.add_argument(
            '--sync-dates-only',
            action='store_true',
            help='Uniquement aligner les dates dette ← vente (pas de création).',
        )

    def handle(self, *args, **options):
        entreprise_id = options['entreprise_id']
        succursale_id = options['succursale_id']
        dry_run = options['dry_run']
        sync_dates_only = options['sync_dates_only']

        if not sync_dates_only:
            sorties = list(
                find_credit_sorties_without_dette(
                    entreprise_id=entreprise_id,
                    succursale_id=succursale_id,
                )
            )
            if not sorties:
                self.stdout.write(self.style.SUCCESS('Aucune vente à crédit orpheline.'))
            else:
                self.stdout.write(f'{len(sorties)} sortie(s) EN_CREDIT sans dette.')
                created = 0
                errors = 0

                for sortie in sorties:
                    label = (
                        f'SORTIE-{sortie.pk} client={sortie.client_id} '
                        f'entreprise={sortie.entreprise_id}'
                    )
                    if dry_run:
                        self.stdout.write(f'[dry-run] {label}')
                        continue
                    try:
                        with transaction.atomic():
                            dette = create_dette_for_credit_sortie(
                                sortie,
                                raise_if_exists=False,
                            )
                        if dette:
                            created += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'OK {label} → dette #{dette.pk} montant={dette.montant_total}'
                                )
                            )
                    except Exception as exc:
                        errors += 1
                        self.stdout.write(self.style.ERROR(f'ERREUR {label}: {exc}'))

                if dry_run:
                    self.stdout.write(self.style.WARNING('Mode dry-run — aucune création.'))
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Terminé : {created} dette(s) créée(s), {errors} erreur(s).'
                        )
                    )

        if dry_run:
            self.stdout.write(self.style.WARNING('Sync dates ignorée en dry-run.'))
            return

        synced = sync_dette_dates_from_sorties(
            entreprise_id=entreprise_id,
            succursale_id=succursale_id,
        )
        self.stdout.write(
            self.style.SUCCESS(f'Dates alignées (dette ← vente) : {synced} dette(s).')
        )
