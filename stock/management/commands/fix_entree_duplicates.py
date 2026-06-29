from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stock.models import Entree, LigneEntree, Stock


class Command(BaseCommand):
    help = (
        "Supprime les lignes d'approvisionnement dupliquees d'une entree ciblee et "
        "reajuste le stock. Utiliser sur les entrees touchees par le bug de double creation."
    )

    def add_arguments(self, parser):
        parser.add_argument('--entree-id', type=int, required=True, help="ID de l'entree a verifier.")
        parser.add_argument(
            '--apply',
            action='store_true',
            help="Applique la suppression des doublons. Sans ce flag, la commande fait seulement un apercu.",
        )

    def handle(self, *args, **options):
        entree_id = options['entree_id']
        apply_changes = options['apply']

        try:
            entree = Entree.objects.get(pk=entree_id)
        except Entree.DoesNotExist as exc:
            raise CommandError(f"Entree #{entree_id} introuvable.") from exc

        lignes = list(
            LigneEntree.objects.filter(entree=entree)
            .select_related('article', 'devise', 'devise_reference')
            .order_by('id')
        )
        if not lignes:
            self.stdout.write(self.style.WARNING(f"Entree #{entree_id} sans ligne."))
            return

        grouped = defaultdict(list)
        for ligne in lignes:
            key = (
                ligne.article_id,
                str(ligne.quantite),
                str(ligne.prix_unitaire),
                str(ligne.prix_vente),
                ligne.date_expiration.isoformat() if ligne.date_expiration else '',
                ligne.devise_id,
                ligne.devise_reference_id,
                str(ligne.taux_change or ''),
                str(ligne.montant_reference),
                str(ligne.seuil_alerte),
            )
            grouped[key].append(ligne)

        duplicates = []
        stock_adjustments = defaultdict(lambda: Decimal('0'))
        for dup_lines in grouped.values():
            if len(dup_lines) < 2:
                continue
            keep = dup_lines[0]
            extra = dup_lines[1:]
            duplicates.append((keep, extra))
            for ligne in extra:
                stock_adjustments[ligne.article_id] += ligne.quantite

        if not duplicates:
            self.stdout.write(self.style.SUCCESS(f"Aucun doublon exact detecte pour l'entree #{entree_id}."))
            return

        total_deleted = sum(len(extra) for _, extra in duplicates)
        self.stdout.write(self.style.WARNING(
            f"Entree #{entree_id}: {total_deleted} ligne(s) dupliquee(s) detectee(s)."
        ))
        for keep, extra in duplicates:
            ids = ', '.join(str(l.pk) for l in extra)
            self.stdout.write(
                f"- Article {keep.article_id} | conserve ligne #{keep.id} | supprime {ids} | quantite a retirer du stock: {sum((l.quantite for l in extra), Decimal('0'))}"
            )

        if not apply_changes:
            self.stdout.write(self.style.WARNING("Apercu uniquement. Relancer avec --apply pour corriger la base."))
            return

        with transaction.atomic():
            delete_ids = [ligne.id for _, extra in duplicates for ligne in extra]
            LigneEntree.objects.filter(id__in=delete_ids).delete()
            for article_id, quantite in stock_adjustments.items():
                stock = Stock.objects.filter(article_id=article_id).first()
                if stock is None:
                    self.stdout.write(self.style.WARNING(
                        f"Stock absent pour l'article {article_id}; ajustement manuel requis ({quantite})."
                    ))
                    continue
                stock.Qte -= quantite
                stock.save(update_fields=['Qte'])

        self.stdout.write(self.style.SUCCESS(
            f"Correction appliquee sur l'entree #{entree_id}. {total_deleted} ligne(s) supprimee(s)."
        ))
