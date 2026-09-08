"""Commande : activer une licence à vie (toutes fonctionnalités, sans expiration)."""
from django.core.management.base import BaseCommand, CommandError

from abonnements.services.licence import activer_acces_a_vie, build_etat_licence
from stock.models import Entreprise


class Command(BaseCommand):
    help = (
        'Active immédiatement le plan À vie pour une entreprise '
        '(date_fin=null, toutes les fonctionnalités).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--entreprise-id',
            type=int,
            required=True,
            help='ID de l\'entreprise à activer.',
        )
        parser.add_argument(
            '--notes',
            type=str,
            default='',
            help='Note libre (ex. motif commercial).',
        )

    def handle(self, *args, **options):
        eid = options['entreprise_id']
        try:
            entreprise = Entreprise.objects.get(pk=eid)
        except Entreprise.DoesNotExist as exc:
            raise CommandError(f'Entreprise #{eid} introuvable.') from exc

        abo = activer_acces_a_vie(entreprise, notes=options.get('notes') or '')
        etat = build_etat_licence(entreprise.id)
        self.stdout.write(
            self.style.SUCCESS(
                f'Licence à vie active pour « {entreprise.nom} » '
                f'(abonnement #{abo.id}, formule={abo.formule.code}).'
            )
        )
        self.stdout.write(
            f'  est_actif={etat["est_actif"]} est_a_vie={etat["est_a_vie"]} '
            f'date_fin={etat["date_fin"]} jours_restants={etat["jours_restants"]}'
        )
