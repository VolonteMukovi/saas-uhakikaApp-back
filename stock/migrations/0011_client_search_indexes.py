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
        if _mysql_has_index(cursor, 'stock_client', 'ft_client_search'):
            return
    schema_editor.execute(
        'ALTER TABLE stock_client ADD FULLTEXT INDEX ft_client_search '
        '(nom, telephone, adresse, email, id)'
    )


def _drop_mysql_fulltext(schema_editor):
    schema_editor.execute('ALTER TABLE stock_client DROP INDEX ft_client_search')


def _add_postgresql_trgm(schema_editor):
    schema_editor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_client_nom_trgm '
        'ON stock_client USING gin (nom gin_trgm_ops)'
    )
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_client_tel_trgm '
        'ON stock_client USING gin ((COALESCE(telephone, \'\')) gin_trgm_ops)'
    )
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_client_adr_trgm '
        'ON stock_client USING gin ((COALESCE(adresse, \'\')) gin_trgm_ops)'
    )
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_client_email_trgm '
        'ON stock_client USING gin ((COALESCE(email, \'\')) gin_trgm_ops)'
    )
    schema_editor.execute(
        'CREATE INDEX IF NOT EXISTS stock_client_id_trgm '
        'ON stock_client USING gin (id gin_trgm_ops)'
    )


def _drop_postgresql_trgm(schema_editor):
    for name in (
        'stock_client_nom_trgm',
        'stock_client_tel_trgm',
        'stock_client_adr_trgm',
        'stock_client_email_trgm',
        'stock_client_id_trgm',
    ):
        schema_editor.execute(f'DROP INDEX IF EXISTS {name}')


def _add_sqlite_fts5(schema_editor):
    schema_editor.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS stock_client_fts USING fts5(
            nom,
            telephone,
            adresse,
            email,
            id,
            content='stock_client',
            content_rowid='rowid'
        )
        """
    )
    schema_editor.execute(
        """
        INSERT INTO stock_client_fts(rowid, nom, telephone, adresse, email, id)
        SELECT rowid, nom, telephone, adresse, email, id FROM stock_client
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_client_ai AFTER INSERT ON stock_client BEGIN
            INSERT INTO stock_client_fts(rowid, nom, telephone, adresse, email, id)
            VALUES (new.rowid, new.nom, new.telephone, new.adresse, new.email, new.id);
        END
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_client_ad AFTER DELETE ON stock_client BEGIN
            INSERT INTO stock_client_fts(stock_client_fts, rowid, nom, telephone, adresse, email, id)
            VALUES('delete', old.rowid, old.nom, old.telephone, old.adresse, old.email, old.id);
        END
        """
    )
    schema_editor.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_client_au AFTER UPDATE ON stock_client BEGIN
            INSERT INTO stock_client_fts(stock_client_fts, rowid, nom, telephone, adresse, email, id)
            VALUES('delete', old.rowid, old.nom, old.telephone, old.adresse, old.email, old.id);
            INSERT INTO stock_client_fts(rowid, nom, telephone, adresse, email, id)
            VALUES (new.rowid, new.nom, new.telephone, new.adresse, new.email, new.id);
        END
        """
    )


def _drop_sqlite_fts5(schema_editor):
    schema_editor.execute('DROP TRIGGER IF EXISTS stock_client_ai')
    schema_editor.execute('DROP TRIGGER IF EXISTS stock_client_ad')
    schema_editor.execute('DROP TRIGGER IF EXISTS stock_client_au')
    schema_editor.execute('DROP TABLE IF EXISTS stock_client_fts')


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
    atomic = False

    dependencies = [
        ('stock', '0010_ensure_mysql_article_fulltext'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
