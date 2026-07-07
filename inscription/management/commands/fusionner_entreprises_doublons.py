"""Fusion prudente des entreprises en double créées pendant l'onboarding."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from inscription.services.entreprise_onboarding import lister_doublons_utilisateur
from inscription.services.entreprise_saas import entreprise_contient_donnees_metier, entreprise_est_configuree
from users.models import Membership
from users.services.membership_context import get_primary_membership

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Analyse et fusionne les entreprises provisoires en double. '
        'Par défaut : simulation (--dry-run).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Appliquer les suppressions (sinon simulation).',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Limiter à un utilisateur.',
        )

    def handle(self, *args, **options):
        dry_run = not options['apply']
        user_id = options.get('user_id')

        qs = User.objects.all().order_by('id')
        if user_id:
            qs = qs.filter(pk=user_id)

        traites = 0
        supprimes = 0
        ignores = 0

        for user in qs.iterator():
            doublons = lister_doublons_utilisateur(user)
            if not doublons:
                continue

            traites += 1
            primary = get_primary_membership(user)
            self.stdout.write(f'\nUtilisateur {user.pk} ({user.email}) — {len(doublons)} entreprises admin')

            for item in doublons:
                flag = ' [PRINCIPALE]' if item['est_principale'] else ''
                self.stdout.write(
                    f"  - #{item['entreprise_id']} {item['nom']!r} "
                    f"config={item['configuration_complete']} "
                    f"donnees={item['donnees_metier']}{flag}"
                )

            for item in doublons:
                if item['est_principale']:
                    continue
                if item['donnees_metier']:
                    self.stdout.write(self.style.WARNING(
                        f"  IGNORÉ #{item['entreprise_id']} : données métier présentes"
                    ))
                    ignores += 1
                    continue
                if item['configuree_metier'] and primary and item['entreprise_id'] != primary.entreprise_id:
                    self.stdout.write(self.style.WARNING(
                        f"  IGNORÉ #{item['entreprise_id']} : entreprise configurée non principale"
                    ))
                    ignores += 1
                    continue

                ent_id = item['entreprise_id']
                if dry_run:
                    self.stdout.write(self.style.NOTICE(
                        f"  [DRY-RUN] Suppression provisoire entreprise #{ent_id}"
                    ))
                else:
                    with transaction.atomic():
                        Membership.objects.filter(
                            user=user,
                            entreprise_id=ent_id,
                        ).delete()
                        from stock.models import Entreprise
                        Entreprise.objects.filter(pk=ent_id).delete()
                    self.stdout.write(self.style.SUCCESS(
                        f"  Supprimé entreprise provisoire #{ent_id}"
                    ))
                supprimes += 1

        mode = 'SIMULATION' if dry_run else 'APPLIQUÉ'
        self.stdout.write(
            f'\n{mode} — utilisateurs avec doublons: {traites}, '
            f'entreprises traitées: {supprimes}, ignorées: {ignores}'
        )
        if dry_run and supprimes:
            self.stdout.write('Relancez avec --apply pour appliquer.')
