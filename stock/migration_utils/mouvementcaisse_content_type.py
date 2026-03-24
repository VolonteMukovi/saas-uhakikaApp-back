"""DDL idempotent pour content_type_id / object_id / utilisateur_id sur MouvementCaisse."""

TABLE = 'stock_mouvementcaisse'
INDEX_NAME = 'stock_mouve_content_354bb1_idx'


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


def _mysql_has_fk(cursor, constraint_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND CONSTRAINT_NAME = %s
        """,
        [TABLE, constraint_name],
    )
    row = cursor.fetchone()
    return row[0] > 0 if row else False


def _pg_has_column(cursor, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s
        """,
        [TABLE, column],
    )
    row = cursor.fetchone()
    return row[0] > 0 if row else False


def _sqlite_columns(cursor) -> set[str]:
    cursor.execute(f'PRAGMA table_info("{TABLE}")')
    return {row[1] for row in cursor.fetchall()}


def ensure_mouvementcaisse_content_type_fields(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor

    with connection.cursor() as cursor:
        if vendor == 'mysql':
            need_ct = not _mysql_has_column(cursor, 'content_type_id')
            need_oid = not _mysql_has_column(cursor, 'object_id')
            need_user = not _mysql_has_column(cursor, 'utilisateur_id')

            if need_ct or need_oid:
                parts = []
                if need_ct:
                    parts.append('ADD COLUMN content_type_id BIGINT NULL')
                if need_oid:
                    parts.append('ADD COLUMN object_id INT UNSIGNED NULL')
                cursor.execute(f'ALTER TABLE {TABLE} {", ".join(parts)}')
            if need_ct and not _mysql_has_fk(cursor, 'stock_mc_ct_id_fk_ensure'):
                cursor.execute(
                    f"""
                    ALTER TABLE {TABLE}
                    ADD CONSTRAINT stock_mc_ct_id_fk_ensure
                    FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) ON DELETE CASCADE
                    """
                )
            if need_user:
                cursor.execute(
                    f"""
                    ALTER TABLE {TABLE}
                    ADD COLUMN utilisateur_id BIGINT NULL,
                    ADD CONSTRAINT stock_mc_user_id_fk_ensure
                    FOREIGN KEY (utilisateur_id) REFERENCES users_user(id) ON DELETE SET NULL
                    """
                )
            if (
                not _mysql_has_index(cursor, INDEX_NAME)
                and _mysql_has_column(cursor, 'content_type_id')
                and _mysql_has_column(cursor, 'object_id')
            ):
                cursor.execute(
                    f'CREATE INDEX {INDEX_NAME} ON {TABLE} (content_type_id, object_id)'
                )
            return

        if vendor == 'postgresql':
            if not _pg_has_column(cursor, 'content_type_id'):
                cursor.execute(
                    f"""
                    ALTER TABLE {TABLE}
                    ADD COLUMN content_type_id BIGINT NULL
                    REFERENCES django_content_type(id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
                    """
                )
            if not _pg_has_column(cursor, 'object_id'):
                cursor.execute(f'ALTER TABLE {TABLE} ADD COLUMN object_id INTEGER NULL')
            if not _pg_has_column(cursor, 'utilisateur_id'):
                cursor.execute(
                    f"""
                    ALTER TABLE {TABLE}
                    ADD COLUMN utilisateur_id BIGINT NULL
                    REFERENCES users_user(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
                    """
                )
            cursor.execute(
                """
                SELECT COUNT(*) FROM pg_indexes
                WHERE schemaname = current_schema() AND tablename = %s AND indexname = %s
                """,
                [TABLE, INDEX_NAME],
            )
            exists = cursor.fetchone()[0] > 0
            if not exists and _pg_has_column(cursor, 'content_type_id') and _pg_has_column(
                cursor, 'object_id'
            ):
                cursor.execute(
                    f'CREATE INDEX {INDEX_NAME} ON {TABLE} (content_type_id, object_id)'
                )
            return

        if vendor == 'sqlite':
            cols = _sqlite_columns(cursor)
            if 'content_type_id' not in cols:
                cursor.execute(
                    f'ALTER TABLE {TABLE} ADD COLUMN content_type_id bigint NULL REFERENCES django_content_type(id)'
                )
            if 'object_id' not in cols:
                cursor.execute(f'ALTER TABLE {TABLE} ADD COLUMN object_id integer NULL')
            if 'utilisateur_id' not in cols:
                cursor.execute(
                    f'ALTER TABLE {TABLE} ADD COLUMN utilisateur_id bigint NULL REFERENCES users_user(id)'
                )
