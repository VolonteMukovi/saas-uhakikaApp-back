"""
Même DDL que 0015 : utile si 0015 a été marquée appliquée sans exécution réelle du SQL
(``--fake``) ou si une ancienne version de 0015 n’avait pas appliqué les colonnes.

Idempotent : sans effet si tout est déjà en place.
"""
from django.db import migrations

from stock.migration_utils.mouvementcaisse_content_type import (
    ensure_mouvementcaisse_content_type_fields,
)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0015_ensure_mouvementcaisse_content_type_fields'),
    ]

    operations = [
        migrations.RunPython(ensure_mouvementcaisse_content_type_fields, backwards),
    ]
