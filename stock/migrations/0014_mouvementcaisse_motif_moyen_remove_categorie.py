# Rétablit motif / moyen sur MouvementCaisse et retire categorie_operation (cf. 0008).
#
# Le DDL est conditionnel : bases sans 0008 (motif/moyen encore présents, pas de
# categorie_operation ni de content_type) faisaient échouer l’ancienne 0014
# (ADD COLUMN motif en double, RemoveField sur une colonne absente), bloquant
# ainsi la migration 0015 qui ajoute content_type_id.

from django.db import migrations, models


TABLE = 'stock_mouvementcaisse'
INDEX_NAME = 'stock_mouve_categor_3d5e8f_idx'


def _mysql_has_column(cursor, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        [TABLE, column],
    )
    row = cursor.fetchone()
    return row[0] > 0 if row else False


def _mysql_has_index(cursor, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.statistics
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        [TABLE, index_name],
    )
    row = cursor.fetchone()
    return row[0] > 0 if row else False


def forwards_0014_database(apps, schema_editor):
    connection = schema_editor.connection
    table = TABLE

    with connection.cursor() as cursor:
        if connection.vendor == 'mysql':
            if not _mysql_has_column(cursor, 'motif'):
                # LONGTEXT sans DEFAULT : compat MySQL 5.7 (TEXT sans défaut explicite)
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN motif LONGTEXT NULL')
            if not _mysql_has_column(cursor, 'moyen'):
                cursor.execute(
                    f'ALTER TABLE {table} ADD COLUMN moyen VARCHAR(30) NULL'
                )
            if _mysql_has_column(cursor, 'categorie_operation'):
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET motif = CONCAT('[', categorie_operation, ']')
                    WHERE (motif IS NULL OR motif = '')
                      AND categorie_operation IS NOT NULL
                      AND categorie_operation != ''
                    """
                )
                if _mysql_has_index(cursor, INDEX_NAME):
                    cursor.execute(f'ALTER TABLE {table} DROP INDEX `{INDEX_NAME}`')
                cursor.execute(f'ALTER TABLE {table} DROP COLUMN categorie_operation')
            return

        if connection.vendor == 'postgresql':
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s
                """,
                [table, 'motif'],
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN motif TEXT NOT NULL DEFAULT \'\'')
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s
                """,
                [table, 'moyen'],
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN moyen VARCHAR(30) NULL')
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s
                """,
                [table, 'categorie_operation'],
            )
            if cursor.fetchone()[0] > 0:
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET motif = '[' || categorie_operation || ']'
                    WHERE (motif IS NULL OR motif = '')
                      AND categorie_operation IS NOT NULL
                      AND categorie_operation != ''
                    """
                )
                cursor.execute(f'DROP INDEX IF EXISTS {INDEX_NAME}')
                cursor.execute(f'ALTER TABLE {table} DROP COLUMN categorie_operation')
            return

        if connection.vendor == 'sqlite':
            cursor.execute(f'PRAGMA table_info({table})')
            cols = {row[1] for row in cursor.fetchall()}
            if 'motif' not in cols:
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN motif TEXT NOT NULL DEFAULT ""')
            if 'moyen' not in cols:
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN moyen VARCHAR(30) NULL')
            if 'categorie_operation' in cols:
                cursor.execute(
                    f"""
                    UPDATE {table}
                    SET motif = '[' || categorie_operation || ']'
                    WHERE (motif IS NULL OR motif = '')
                      AND categorie_operation IS NOT NULL
                      AND categorie_operation != ''
                    """
                )
                # SQLite : pas de DROP COLUMN simple avant 3.35 ; Django 5.2 gère ailleurs
                try:
                    cursor.execute(f'DROP INDEX IF EXISTS {INDEX_NAME}')
                except Exception:
                    pass
                # Si la colonne reste (SQLite ancien), l’état Django sera quand même cohérent
                try:
                    cursor.execute(f'ALTER TABLE {table} DROP COLUMN categorie_operation')
                except Exception:
                    pass


def backwards_0014_database(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0013_sortie_rename_libelle_to_motif'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(forwards_0014_database, backwards_0014_database),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='mouvementcaisse',
                    name='motif',
                    field=models.TextField(blank=True, default=''),
                ),
                migrations.AddField(
                    model_name='mouvementcaisse',
                    name='moyen',
                    field=models.CharField(blank=True, max_length=30, null=True),
                ),
                migrations.RemoveIndex(
                    model_name='mouvementcaisse',
                    name='stock_mouve_categor_3d5e8f_idx',
                ),
                migrations.RemoveField(
                    model_name='mouvementcaisse',
                    name='categorie_operation',
                ),
            ],
        ),
    ]
