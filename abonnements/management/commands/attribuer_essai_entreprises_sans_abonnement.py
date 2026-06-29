"""Commande : attribuer un essai gratuit aux entreprises sans abonnement."""
from django.core.management.base import BaseCommand

from abonnements.models import AbonnementEntreprise
from abonnements.services.licence import demarrer_essai_gratuit
from stock.models import Entreprise


class Command(BaseCommand):
    help = 'Démarre l\'essai gratuit pour les entreprises existantes sans abonnement courant.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche les entreprises concernées sans modifier la base.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        entreprises_sans_abo = Entreprise.objects.exclude(
            abonnements__est_courant=True,
        ).order_by('id')

        count = entreprises_sans_abo.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('Toutes les entreprises ont déjà un abonnement courant.'))
            return

        self.stdout.write(f'{count} entreprise(s) sans abonnement courant.')

        for ent in entreprises_sans_abo:
            if dry_run:
                self.stdout.write(f'  [dry-run] Essai à créer : {ent.id} — {ent.nom}')
                continue
            abo = demarrer_essai_gratuit(ent)
            self.stdout.write(
                self.style.SUCCESS(f'  Essai créé : {ent.nom} → fin {abo.date_fin.date()}')
            )

        if dry_run:
            self.stdout.write('Relancez sans --dry-run pour appliquer.')
