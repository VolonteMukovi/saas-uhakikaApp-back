"""
DDL idempotent pour la migration 0008 (multicaisse + GFK sur MouvementCaisse).

Utile lorsque la base est dans un état partiel (ex. tables detail/type créées mais
ALTER sur stock_mouvementcaisse non exécuté), ce qui faisait échouer migrate.
"""


def _conn(schema_editor):
    return schema_editor.connection


def _mysql_cols(cursor, table: str) -> set[str]:
    cursor.execute(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        [table],
    )
    return {row[0] for row in cursor.fetchall()}


def _mysql_table_exists(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        [table],
    )
    return cursor.fetchone()[0] > 0


def _mysql_fk_exists_on_column(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
          AND COLUMN_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
        """,
        [table, column],
    )
    return cursor.fetchone()[0] > 0


def _mysql_index_exists(cursor, table: str, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.statistics
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
        """,
        [table, index_name],
    )
    return cursor.fetchone()[0] > 0


def _mysql_column_type(cursor, table: str, column: str) -> str:
    """
    Type SQL exact de la colonne (ex. bigint(20), int(11), bigint(20) unsigned).
    Nécessaire pour les FK : InnoDB exige la même définition que la colonne référencée
    (sinon errno 150), y compris INT vs BIGINT et UNSIGNED.
    """
    cursor.execute(
        """
        SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        [table, column],
    )
    row = cursor.fetchone()
    if not row:
        raise RuntimeError(
            f'apply_0008_idempotent: colonne `{table}`.`{column}` introuvable.'
        )
    return row[0]


def _mysql_ensure_innodb(cursor, table: str) -> None:
    """InnoDB est requis pour les clés étrangères (errno 150 si MyISAM / autre)."""
    cursor.execute(
        """
        SELECT ENGINE FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        [table],
    )
    row = cursor.fetchone()
    if row and row[0] and str(row[0]).upper() != "INNODB":
        cursor.execute(f"ALTER TABLE `{table}` ENGINE=InnoDB")


def _mysql_drop_fk_by_column(cursor, table: str, column: str) -> None:
    cursor.execute(
        """
        SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
          AND COLUMN_NAME = %s AND REFERENCED_TABLE_NAME IS NOT NULL
        """,
        [table, column],
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(f'ALTER TABLE `{table}` DROP FOREIGN KEY `{row[0]}`')


def apply_0008_idempotent(apps, schema_editor) -> None:
    connection = _conn(schema_editor)
    if connection.vendor != 'mysql':
        raise NotImplementedError(
            'apply_0008_idempotent est implémenté pour MySQL uniquement. '
            'Sur PostgreSQL/SQLite, utilisez une base neuve ou appliquez 0008 sur une copie.'
        )

    with connection.cursor() as cursor:
        # --- 1–2 : tables sans FK d’abord (comme Django) ---
        if not _mysql_table_exists(cursor, 'stock_detailmouvementcaisse'):
            cursor.execute(
                """
                CREATE TABLE `stock_detailmouvementcaisse` (
                  `id` bigint NOT NULL AUTO_INCREMENT,
                  `montant` decimal(12,2) NOT NULL,
                  `motif_explicite` longtext NOT NULL,
                  `reference_piece` varchar(100) NOT NULL,
                  PRIMARY KEY (`id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        if not _mysql_table_exists(cursor, 'stock_typecaisse'):
            cursor.execute(
                """
                CREATE TABLE `stock_typecaisse` (
                  `id` bigint NOT NULL AUTO_INCREMENT,
                  `libelle` varchar(120) NOT NULL,
                  `description` longtext NOT NULL,
                  `image` varchar(100) NULL,
                  `is_active` bool NOT NULL,
                  `created_at` datetime(6) NOT NULL,
                  PRIMARY KEY (`id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

        # --- 3 : PaiementDette : retirer les FK puis la table ---
        if _mysql_table_exists(cursor, 'stock_paiementdette'):
            fk_cols = (
                'dette_id',
                'devise_id',
                'entreprise_id',
                'succursale_id',
                'utilisateur_id',
            )
            for col in fk_cols:
                _mysql_drop_fk_by_column(cursor, 'stock_paiementdette', col)
            for col in fk_cols:
                cols_pt = _mysql_cols(cursor, 'stock_paiementdette')
                if col in cols_pt:
                    cursor.execute(
                        f'ALTER TABLE `stock_paiementdette` DROP COLUMN `{col}`'
                    )
            cursor.execute('DROP TABLE IF EXISTS `stock_paiementdette`')

        # --- 4 : DetteClient ---
        dc = _mysql_cols(cursor, 'stock_detteclient')
        if 'montant_paye' in dc:
            cursor.execute('ALTER TABLE `stock_detteclient` DROP COLUMN `montant_paye`')
        if 'solde_restant' in dc:
            cursor.execute('ALTER TABLE `stock_detteclient` DROP COLUMN `solde_restant`')

        # --- 5–6 : MouvementCaisse motif/moyen ---
        mc = _mysql_cols(cursor, 'stock_mouvementcaisse')
        if 'motif' in mc:
            cursor.execute('ALTER TABLE `stock_mouvementcaisse` DROP COLUMN `motif`')
        if 'moyen' in mc:
            cursor.execute('ALTER TABLE `stock_mouvementcaisse` DROP COLUMN `moyen`')

        # --- 7 : Sortie : motif -> libelle (état intermédiaire 0008) ---
        sc = _mysql_cols(cursor, 'stock_sortie')
        if 'motif' in sc and 'libelle' not in sc:
            cursor.execute(
                'ALTER TABLE `stock_sortie` ADD COLUMN `libelle` varchar(255) NOT NULL DEFAULT ""'
            )
            cursor.execute('UPDATE `stock_sortie` SET `libelle` = COALESCE(`motif`, "")')
            cursor.execute('ALTER TABLE `stock_sortie` DROP COLUMN `motif`')
        elif 'libelle' not in sc and 'motif' not in sc:
            cursor.execute(
                'ALTER TABLE `stock_sortie` ADD COLUMN `libelle` varchar(255) NOT NULL DEFAULT ""'
            )

        # --- 8–12 : MouvementCaisse champs 0008 ---
        mc = _mysql_cols(cursor, 'stock_mouvementcaisse')
        if 'categorie_operation' not in mc:
            cursor.execute(
                """
                ALTER TABLE `stock_mouvementcaisse`
                ADD COLUMN `categorie_operation` varchar(32) NOT NULL DEFAULT 'MANUEL'
                """
            )
            cursor.execute(
                'ALTER TABLE `stock_mouvementcaisse` ALTER COLUMN `categorie_operation` DROP DEFAULT'
            )
        if 'content_type_id' not in mc:
            _mysql_ensure_innodb(cursor, "stock_mouvementcaisse")
            _mysql_ensure_innodb(cursor, "django_content_type")
            ct_type = _mysql_column_type(cursor, "django_content_type", "id")
            cursor.execute(
                f"""
                ALTER TABLE `stock_mouvementcaisse`
                ADD COLUMN `content_type_id` {ct_type} NULL,
                ADD CONSTRAINT `stock_mouvementcaiss_content_type_id_ad2b8e25_fk_django_co`
                FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type`(`id`)
                """
            )
        if 'object_id' not in mc:
            cursor.execute(
                """
                ALTER TABLE `stock_mouvementcaisse`
                ADD COLUMN `object_id` integer UNSIGNED NULL
                """
            )
        if 'utilisateur_id' not in mc:
            _mysql_ensure_innodb(cursor, "stock_mouvementcaisse")
            _mysql_ensure_innodb(cursor, "users_user")
            uid_type = _mysql_column_type(cursor, 'users_user', 'id')
            cursor.execute(
                f"""
                ALTER TABLE `stock_mouvementcaisse`
                ADD COLUMN `utilisateur_id` {uid_type} NULL,
                ADD CONSTRAINT `stock_mouvementcaisse_utilisateur_id_75557a2a_fk_users_user_id`
                FOREIGN KEY (`utilisateur_id`) REFERENCES `users_user`(`id`)
                """
            )

        if 'reference_piece' in mc:
            cursor.execute(
                "UPDATE `stock_mouvementcaisse` SET `reference_piece` = '' WHERE `reference_piece` IS NULL"
            )
            cursor.execute(
                'ALTER TABLE `stock_mouvementcaisse` MODIFY COLUMN `reference_piece` varchar(100) NOT NULL'
            )

        if not _mysql_index_exists(cursor, 'stock_mouvementcaisse', 'stock_mouve_content_354bb1_idx'):
            cursor.execute(
                """
                CREATE INDEX `stock_mouve_content_354bb1_idx`
                ON `stock_mouvementcaisse` (`content_type_id`, `object_id`)
                """
            )
        if not _mysql_index_exists(cursor, 'stock_mouvementcaisse', 'stock_mouve_categor_3d5e8f_idx'):
            cursor.execute(
                """
                CREATE INDEX `stock_mouve_categor_3d5e8f_idx`
                ON `stock_mouvementcaisse` (`categorie_operation`)
                """
            )

        # --- 13 : Detail : mouvement_id (NOT NULL) ---
        dcols = _mysql_cols(cursor, 'stock_detailmouvementcaisse')
        if 'mouvement_id' not in dcols:
            cursor.execute('DELETE FROM `stock_detailmouvementcaisse`')
            _mysql_ensure_innodb(cursor, "stock_detailmouvementcaisse")
            _mysql_ensure_innodb(cursor, "stock_mouvementcaisse")
            mid_type = _mysql_column_type(cursor, 'stock_mouvementcaisse', 'id')
            cursor.execute(
                f"""
                ALTER TABLE `stock_detailmouvementcaisse`
                ADD COLUMN `mouvement_id` {mid_type} NOT NULL,
                ADD CONSTRAINT `stock_detailmouvemen_mouvement_id_bad96ba0_fk_stock_mou`
                FOREIGN KEY (`mouvement_id`) REFERENCES `stock_mouvementcaisse`(`id`)
                """
            )
        elif not _mysql_fk_exists_on_column(
            cursor, "stock_detailmouvementcaisse", "mouvement_id"
        ):
            _mysql_ensure_innodb(cursor, "stock_detailmouvementcaisse")
            _mysql_ensure_innodb(cursor, "stock_mouvementcaisse")
            cursor.execute(
                """
                ALTER TABLE `stock_detailmouvementcaisse`
                ADD CONSTRAINT `stock_detailmouvemen_mouvement_id_bad96ba0_fk_stock_mou`
                FOREIGN KEY (`mouvement_id`) REFERENCES `stock_mouvementcaisse`(`id`)
                """
            )

        # --- 14 : TypeCaisse FKs ---
        dcols = _mysql_cols(cursor, 'stock_detailmouvementcaisse')
        if 'type_caisse_id' in dcols:
            _mysql_drop_fk_by_column(
                cursor, 'stock_detailmouvementcaisse', 'type_caisse_id'
            )
            cursor.execute(
                'UPDATE `stock_detailmouvementcaisse` SET `type_caisse_id` = NULL'
            )

        tc = _mysql_cols(cursor, 'stock_typecaisse')
        if 'entreprise_id' not in tc:
            cursor.execute('DELETE FROM `stock_typecaisse`')
            _mysql_ensure_innodb(cursor, "stock_typecaisse")
            _mysql_ensure_innodb(cursor, "stock_entreprise")
            eid_type = _mysql_column_type(cursor, 'stock_entreprise', 'id')
            cursor.execute(
                f"""
                ALTER TABLE `stock_typecaisse`
                ADD COLUMN `entreprise_id` {eid_type} NOT NULL,
                ADD CONSTRAINT `stock_typecaisse_entreprise_id_2d650062_fk_stock_entreprise_id`
                FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise`(`id`)
                """
            )
        if 'succursale_id' not in tc:
            _mysql_ensure_innodb(cursor, "stock_typecaisse")
            _mysql_ensure_innodb(cursor, "stock_succursale")
            sid_type = _mysql_column_type(cursor, 'stock_succursale', 'id')
            cursor.execute(
                f"""
                ALTER TABLE `stock_typecaisse`
                ADD COLUMN `succursale_id` {sid_type} NULL,
                ADD CONSTRAINT `stock_typecaisse_succursale_id_8ddbed50_fk_stock_succursale_id`
                FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale`(`id`)
                """
            )

        if not _mysql_index_exists(cursor, 'stock_typecaisse', 'stock_typec_entrepr_4f8295_idx'):
            cursor.execute(
                'CREATE INDEX `stock_typec_entrepr_4f8295_idx` ON `stock_typecaisse` (`entreprise_id`)'
            )
        if not _mysql_index_exists(cursor, 'stock_typecaisse', 'stock_typec_entrepr_abb535_idx'):
            cursor.execute(
                """
                CREATE INDEX `stock_typec_entrepr_abb535_idx`
                ON `stock_typecaisse` (`entreprise_id`, `succursale_id`)
                """
            )

        # --- 15 : Detail type_caisse ---
        dcols = _mysql_cols(cursor, 'stock_detailmouvementcaisse')
        if 'type_caisse_id' not in dcols:
            _mysql_ensure_innodb(cursor, "stock_detailmouvementcaisse")
            _mysql_ensure_innodb(cursor, "stock_typecaisse")
            tcid_type = _mysql_column_type(cursor, 'stock_typecaisse', 'id')
            cursor.execute(
                f"""
                ALTER TABLE `stock_detailmouvementcaisse`
                ADD COLUMN `type_caisse_id` {tcid_type} NULL,
                ADD CONSTRAINT `stock_detailmouvemen_type_caisse_id_9c09512f_fk_stock_typ`
                FOREIGN KEY (`type_caisse_id`) REFERENCES `stock_typecaisse`(`id`)
                """
            )


def backwards_noop(apps, schema_editor) -> None:
    pass
