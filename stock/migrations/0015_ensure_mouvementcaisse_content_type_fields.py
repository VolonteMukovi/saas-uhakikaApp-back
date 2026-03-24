"""
Garantit les colonnes GenericForeignKey sur ``stock_mouvementcaisse`` si la base
n'a jamais reçu le DDL de la migration 0008.

Voir ``utils_ensure_mouvementcaisse_content_type.py`` (logique idempotente partagée).
"""
from django.db import migrations

from stock.migration_utils.mouvementcaisse_content_type import (
    ensure_mouvementcaisse_content_type_fields,
)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0014_mouvementcaisse_motif_moyen_remove_categorie'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(ensure_mouvementcaisse_content_type_fields, backwards),
    ]
