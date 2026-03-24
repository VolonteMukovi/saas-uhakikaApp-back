from django.db import migrations


def _mysql_has_index(cursor, table: str, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.statistics
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        [table, index_name],
    )
    return cursor.fetchone()[0] > 0


def _add_mysql_fulltext(schema_editor):
    with schema_editor.connection.cursor() as cursor:
        if _mysql_has_index(cursor, 'stock_article', 'ft_article_search'):
            return
    schema_editor.execute(
        'ALTER TABLE stock_article ADD FULLTEXT INDEX ft_article_search '
        '(nom_scientifique, nom_commercial, article_id)'
    )


def _drop_mysql_fulltext(schema_editor):
    schema_editor.execute('ALTER TABLE stock_article DROP INDEX ft_article_search')


def _add_postgresql_trgm(schema_editor):
    schema_editor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_article_nom_sci_trgm '
        'ON stock_article USING gin (nom_scientifique gin_trgm_ops)'
    )
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_article_nom_com_trgm '
        'ON stock_article USING gin ((COALESCE(nom_commercial, \'\')) gin_trgm_ops)'
    )
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_article_art_id_trgm '
        'ON stock_article USING gin (article_id gin_trgm_ops)'
    )


def _drop_postgresql_trgm(schema_editor):
    schema_editor.execute('DROP INDEX IF EXISTS stock_article_nom_sci_trgm')
    schema_editor.execute('DROP INDEX IF EXISTS stock_article_nom_com_trgm')
    schema_editor.execute('DROP INDEX IF EXISTS stock_article_art_id_trgm')


def _add_sqlite_fts5(schema_editor):
    # Table FTS5 liée à stock_article (content) pour recherche tolérante / préfixes
    schema_editor.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS stock_article_fts USING fts5(
            nom_scientifique,
            nom_commercial,
            article_id,
            content='stock_article',
            content_rowid='rowid'
        )
        """
    )
    schema_editor.execute(
        """
        INSERT INTO stock_article_fts(rowid, nom_scientifique, nom_commercial, article_id)
        SELECT rowid, nom_scientifique, nom_commercial, article_id FROM stock_article
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_article_ai AFTER INSERT ON stock_article BEGIN
            INSERT INTO stock_article_fts(rowid, nom_scientifique, nom_commercial, article_id)
            VALUES (new.rowid, new.nom_scientifique, new.nom_commercial, new.article_id);
        END
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_article_ad AFTER DELETE ON stock_article BEGIN
            INSERT INTO stock_article_fts(stock_article_fts, rowid, nom_scientifique, nom_commercial, article_id)
            VALUES('delete', old.rowid, old.nom_scientifique, old.nom_commercial, old.article_id);
        END
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_article_au AFTER UPDATE ON stock_article BEGIN
            INSERT INTO stock_article_fts(stock_article_fts, rowid, nom_scientifique, nom_commercial, article_id)
            VALUES('delete', old.rowid, old.nom_scientifique, old.nom_commercial, old.article_id);
            INSERT INTO stock_article_fts(rowid, nom_scientifique, nom_commercial, article_id)
            VALUES (new.rowid, new.nom_scientifique, new.nom_commercial, new.article_id);
        END
        """
    )


def _drop_sqlite_fts5(schema_editor):
    schema_editor.execute('DROP TRIGGER IF EXISTS stock_article_ai')
    schema_editor.execute('DROP TRIGGER IF EXISTS stock_article_ad')
    schema_editor.execute('DROP TRIGGER IF EXISTS stock_article_au')
    schema_editor.execute('DROP TABLE IF EXISTS stock_article_fts')


def forwards(apps, schema_editor):
    v = schema_editor.connection.vendor
    if v == 'mysql':
        _add_mysql_fulltext(schema_editor)
    elif v == 'postgresql':
        _add_postgresql_trgm(schema_editor)
    elif v == 'sqlite':
        _add_sqlite_fts5(schema_editor)


def backwards(apps, schema_editor):
    v = schema_editor.connection.vendor
    if v == 'mysql':
        _drop_mysql_fulltext(schema_editor)
    elif v == 'postgresql':
        _drop_postgresql_trgm(schema_editor)
    elif v == 'sqlite':
        _drop_sqlite_fts5(schema_editor)


class Migration(migrations.Migration):
    # DDL MySQL (FULLTEXT) hors transaction
    atomic = False

    dependencies = [
        ('stock', '0008_detailmouvementcaisse_typecaisse_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
