"""Garantit l'index FULLTEXT ft_client_search sur MySQL si absent (cf. 0010 articles)."""
from django.db import migrations


def _mysql_has_fulltext_index(schema_editor) -> bool:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'stock_client'
              AND index_name = 'ft_client_search'
            """
        )
        row = cursor.fetchone()
        return row[0] > 0 if row else False


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    if _mysql_has_fulltext_index(schema_editor):
        return
    schema_editor.execute(
        'ALTER TABLE stock_client ADD FULLTEXT INDEX ft_client_search '
        '(nom, telephone, adresse, email, id)'
    )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    if not _mysql_has_fulltext_index(schema_editor):
        return
    schema_editor.execute('ALTER TABLE stock_client DROP INDEX ft_client_search')


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('stock', '0011_client_search_indexes'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
