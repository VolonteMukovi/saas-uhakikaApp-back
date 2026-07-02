"""
Audit des mouvements de caisse créés automatiquement par les approvisionnements (ancienne logique).

Ne supprime rien par défaut. Utiliser --apply pour annuler (soft) les mouvements identifiés
comme générés automatiquement à partir d'une entrée stock.

Critères d'identification :
- entree_id renseigné sur MouvementCaisse
- categorie APPROVISIONNEMENT
- ou reference_piece commençant par APPRO-, AJ-ENT-, ANN-ENT-
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from caisse.models import MouvementCaisse


AUTO_REF_PREFIXES = ('APPRO-', 'AJ-ENT-', 'ANN-ENT-')


def queryset_mouvements_auto_appro():
    q = Q(entree_id__isnull=False)
    q &= (
        Q(categorie='APPROVISIONNEMENT')
        | Q(reference_piece__startswith='APPRO-')
        | Q(reference_piece__startswith='AJ-ENT-')
        | Q(reference_piece__startswith='ANN-ENT-')
    )
    return MouvementCaisse.objects.filter(q).select_related(
        'entree', 'devise', 'type_caisse', 'entreprise'
    ).order_by('id')


class Command(BaseCommand):
    help = (
        'Liste les mouvements de caisse liés automatiquement aux approvisionnements. '
        'Option --apply : marque motif [ANNULÉ-AUTO-APPRO] (ne supprime pas la ligne).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--entreprise-id',
            type=int,
            default=None,
            help='Filtrer par entreprise',
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Marquer les mouvements identifiés (ajout préfixe motif, sans suppression)',
        )

    def handle(self, *args, **options):
        qs = queryset_mouvements_auto_appro()
        eid = options.get('entreprise_id')
        if eid:
            qs = qs.filter(entreprise_id=eid)

        rows = list(qs)
        if not rows:
            self.stdout.write(self.style.SUCCESS('Aucun mouvement auto-approvisionnement trouvé.'))
            return

        self.stdout.write(f'{len(rows)} mouvement(s) potentiellement auto-généré(s) :\n')
        for mv in rows:
            entree_label = f'entree#{mv.entree_id}' if mv.entree_id else '-'
            self.stdout.write(
                f'  id={mv.pk} {mv.type} {mv.montant} {getattr(mv.devise, "sigle", "?")} '
                f'cat={mv.categorie} ref={mv.reference_piece!r} {entree_label} '
                f'entreprise={mv.entreprise_id}'
            )

        if not options['apply']:
            self.stdout.write(
                '\nMode lecture seule. Relancer avec --apply pour marquer les mouvements '
                '(motif préfixé [ANNULÉ-AUTO-APPRO], sans suppression physique).'
            )
            self.stdout.write(
                'Vérifiez manuellement les lignes avant toute correction comptable définitive.'
            )
            return

        marker = '[ANNULÉ-AUTO-APPRO] '
        updated = 0
        with transaction.atomic():
            for mv in rows:
                if mv.motif and mv.motif.startswith('[ANNULÉ-AUTO-APPRO]'):
                    continue
                mv.motif = f'{marker}{mv.motif or "Mouvement auto approvisionnement"}'
                mv.save(update_fields=['motif'])
                updated += 1

        self.stdout.write(self.style.WARNING(f'{updated} mouvement(s) marqué(s).'))
        self.stdout.write(
            'Les soldes historiques incluent encore ces lignes tant qu\'elles ne sont pas '
            'contre-passées manuellement ou supprimées après validation métier.'
        )
