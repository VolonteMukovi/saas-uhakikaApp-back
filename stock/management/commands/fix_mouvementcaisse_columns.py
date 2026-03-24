"""
Ajoute ``content_type_id`` / ``object_id`` / ``utilisateur_id`` sur ``stock_mouvementcaisse``
si la migration n’a pas été exécutée (même logique que 0015 / 0016).

Usage::
    python manage.py fix_mouvementcaisse_columns
"""
from django.core.management.base import BaseCommand
from django.db import connection

from stock.db_compat import mouvementcaisse_column_names
from stock.migration_utils.mouvementcaisse_content_type import (
    ensure_mouvementcaisse_content_type_fields,
)


class Command(BaseCommand):
    help = 'Ajoute les colonnes GFK manquantes sur stock_mouvementcaisse (MySQL/PG/SQLite).'

    def handle(self, *args, **options):
        with connection.schema_editor() as schema_editor:
            ensure_mouvementcaisse_content_type_fields(None, schema_editor)
        self.stdout.write(self.style.SUCCESS('Colonnes MouvementCaisse vérifiées / ajoutées.'))
        self.stdout.write(f'Colonnes actuelles : {sorted(mouvementcaisse_column_names())}')
