"""
Sur MySQL : garantit l'index FULLTEXT ft_article_search si absent.

Utile lorsque la migration 0009 a été enregistrée comme appliquée sur un autre
moteur (ex. SQLite en dev) alors que la base réelle est MySQL : l'index n'existe pas
et MATCH ... AGAINST provoque l'erreur 1191.
"""
from django.db import migrations


def _mysql_has_fulltext_index(schema_editor) -> bool:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = 'stock_article'
              AND index_name = 'ft_article_search'
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
        'ALTER TABLE stock_article ADD FULLTEXT INDEX ft_article_search '
        '(nom_scientifique, nom_commercial, article_id)'
    )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    if not _mysql_has_fulltext_index(schema_editor):
        return
    schema_editor.execute('ALTER TABLE stock_article DROP INDEX ft_article_search')


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('stock', '0009_article_fulltext_search'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
