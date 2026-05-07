from django.db import migrations


def cleanup_legacy_client_columns(apps, schema_editor):
    connection = schema_editor.connection
    qn = schema_editor.quote_name

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))

    client_table = 'stock_client'
    link_table = 'stock_cliententreprise'

    if client_table not in tables:
        return

    with connection.cursor() as cursor:
        desc = connection.introspection.get_table_description(cursor, client_table)
    client_columns = {getattr(c, 'name', c[0]) for c in desc}

    # Backfill links one more time from legacy columns if still present.
    if link_table in tables and {'entreprise_id', 'succursale_id', 'is_special'}.issubset(client_columns):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT IGNORE INTO {qn(link_table)}
                    (client_id, entreprise_id, succursale_id, is_special)
                SELECT
                    id,
                    entreprise_id,
                    succursale_id,
                    COALESCE(is_special, 0)
                FROM {qn(client_table)}
                WHERE entreprise_id IS NOT NULL
                """
            )

    # Ensure DB-level default for strict-mode inserts.
    if link_table in tables:
        with connection.cursor() as cursor:
            cursor.execute(
                f"ALTER TABLE {qn(link_table)} MODIFY COLUMN is_special TINYINT(1) NOT NULL DEFAULT 0"
            )

    # Drop FKs on legacy columns before dropping columns.
    legacy_cols = ('entreprise_id', 'succursale_id')
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME IN (%s, %s)
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """,
            [client_table, legacy_cols[0], legacy_cols[1]],
        )
        fk_names = [row[0] for row in cursor.fetchall()]

    for fk_name in fk_names:
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {qn(client_table)} DROP FOREIGN KEY {qn(fk_name)}")

    # Drop old indexes if they still exist.
    obsolete_indexes = (
        'stock_clien_entrepr_f00fc4_idx',
        'stock_clien_succurs_353de2_idx',
        'stock_clien_entrepr_2611a1_idx',
        'stock_clien_entrepr_513664_idx',
    )
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW INDEX FROM {qn(client_table)}")
        existing_index_names = {row[2] for row in cursor.fetchall()}

    for idx in obsolete_indexes:
        if idx in existing_index_names:
            with connection.cursor() as cursor:
                cursor.execute(f"ALTER TABLE {qn(client_table)} DROP INDEX {qn(idx)}")

    # Finally remove legacy columns from stock_client.
    for col in ('entreprise_id', 'succursale_id', 'is_special'):
        if col in client_columns:
            with connection.cursor() as cursor:
                cursor.execute(f"ALTER TABLE {qn(client_table)} DROP COLUMN {qn(col)}")


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('stock', '0025_repair_client_schema_after_fake'),
    ]

    operations = [
        migrations.RunPython(cleanup_legacy_client_columns, migrations.RunPython.noop),
    ]
