"""
Rétablit le champ `motif` sur Sortie (nom de colonne `motif` en base).

Après 0008, le modèle utilisait `libelle` ; on revient à `motif` comme à l’origine.
- Si la colonne `libelle` existe : renommage en `motif` (données conservées).
- Si seule `motif` existe : rien à faire côté SQL (bases n’ayant pas appliqué 0008).
"""
from django.db import migrations


def _table_columns(schema_editor, table: str) -> set[str]:
    with schema_editor.connection.cursor() as cursor:
        if schema_editor.connection.vendor == 'mysql':
            cursor.execute(
                """
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                """,
                [table],
            )
        elif schema_editor.connection.vendor == 'postgresql':
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = %s
                """,
                [table],
            )
        else:
            cursor.execute(f'PRAGMA table_info("{table}")')
            return {row[1] for row in cursor.fetchall()}
        return {row[0] for row in cursor.fetchall()}


def forwards_db(apps, schema_editor):
    table = 'stock_sortie'
    cols = _table_columns(schema_editor, table)
    if 'libelle' not in cols:
        return
    v = schema_editor.connection.vendor
    if v == 'mysql':
        schema_editor.execute(
            'ALTER TABLE stock_sortie CHANGE COLUMN libelle motif VARCHAR(255) NULL'
        )
    elif v == 'postgresql':
        schema_editor.execute(
            'ALTER TABLE stock_sortie RENAME COLUMN libelle TO motif'
        )
    elif v == 'sqlite':
        schema_editor.execute(
            'ALTER TABLE stock_sortie RENAME COLUMN libelle TO motif'
        )


def backwards_db(apps, schema_editor):
    table = 'stock_sortie'
    cols = _table_columns(schema_editor, table)
    if 'motif' not in cols or 'libelle' in cols:
        return
    v = schema_editor.connection.vendor
    if v == 'mysql':
        schema_editor.execute(
            'ALTER TABLE stock_sortie CHANGE COLUMN motif libelle VARCHAR(255) NULL'
        )
    elif v == 'postgresql':
        schema_editor.execute(
            'ALTER TABLE stock_sortie RENAME COLUMN motif TO libelle'
        )
    elif v == 'sqlite':
        schema_editor.execute(
            'ALTER TABLE stock_sortie RENAME COLUMN motif TO libelle'
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('stock', '0012_ensure_mysql_client_fulltext'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(forwards_db, backwards_db),
            ],
            state_operations=[
                migrations.RenameField(
                    model_name='sortie',
                    old_name='libelle',
                    new_name='motif',
                ),
            ],
        ),
    ]
