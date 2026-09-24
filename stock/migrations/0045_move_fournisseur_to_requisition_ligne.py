# Generated manually — corrige l'écart DB vs migration 0044 réécrite.
# Ancienne 0044 (appliquée) : fournisseur sur stock_requisition.
# Nouvelle 0044 (fichiers) : fournisseur sur stock_requisitionligne.
# Cette migration aligne la base sans toucher l'état Django déjà cohérent.
# Idempotente : ignore DROP/ADD si l'objet n'existe déjà plus / existe déjà.

from django.db import migrations


def _index_exists(cursor, table: str, index_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        LIMIT 1
        """,
        [table, index_name],
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        [table, column],
    )
    return cursor.fetchone() is not None


def _fk_exists(cursor, table: str, constraint: str) -> bool:
    cursor.execute(
        """
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND constraint_name = %s
          AND constraint_type = 'FOREIGN KEY'
        LIMIT 1
        """,
        [table, constraint],
    )
    return cursor.fetchone() is not None


def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        if _index_exists(cursor, "stock_requisition", "stock_req_ent_fou_idx"):
            cursor.execute("ALTER TABLE `stock_requisition` DROP INDEX `stock_req_ent_fou_idx`")
        if _fk_exists(cursor, "stock_requisition", "stock_requisition_fournisseur_id_c2f1a425_fk_order_fou"):
            cursor.execute(
                "ALTER TABLE `stock_requisition` "
                "DROP FOREIGN KEY `stock_requisition_fournisseur_id_c2f1a425_fk_order_fou`"
            )
        if _column_exists(cursor, "stock_requisition", "fournisseur_id"):
            cursor.execute("ALTER TABLE `stock_requisition` DROP COLUMN `fournisseur_id`")

        if not _column_exists(cursor, "stock_requisitionligne", "fournisseur_id"):
            cursor.execute(
                "ALTER TABLE `stock_requisitionligne` "
                "ADD COLUMN `fournisseur_id` BIGINT NULL"
            )
        if not _fk_exists(cursor, "stock_requisitionligne", "stock_requisitionligne_fournisseur_id_fk_order_fou"):
            cursor.execute(
                "ALTER TABLE `stock_requisitionligne` "
                "ADD CONSTRAINT `stock_requisitionligne_fournisseur_id_fk_order_fou` "
                "FOREIGN KEY (`fournisseur_id`) REFERENCES `order_fournisseur` (`id`) "
                "ON DELETE SET NULL"
            )
        if not _index_exists(cursor, "stock_requisitionligne", "stock_reqligne_fou_idx"):
            cursor.execute(
                "CREATE INDEX `stock_reqligne_fou_idx` "
                "ON `stock_requisitionligne` (`requisition_id`, `fournisseur_id`)"
            )


def backwards(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        if _index_exists(cursor, "stock_requisitionligne", "stock_reqligne_fou_idx"):
            cursor.execute("ALTER TABLE `stock_requisitionligne` DROP INDEX `stock_reqligne_fou_idx`")
        if _fk_exists(cursor, "stock_requisitionligne", "stock_requisitionligne_fournisseur_id_fk_order_fou"):
            cursor.execute(
                "ALTER TABLE `stock_requisitionligne` "
                "DROP FOREIGN KEY `stock_requisitionligne_fournisseur_id_fk_order_fou`"
            )
        if _column_exists(cursor, "stock_requisitionligne", "fournisseur_id"):
            cursor.execute("ALTER TABLE `stock_requisitionligne` DROP COLUMN `fournisseur_id`")

        if not _column_exists(cursor, "stock_requisition", "fournisseur_id"):
            cursor.execute(
                "ALTER TABLE `stock_requisition` ADD COLUMN `fournisseur_id` BIGINT NULL"
            )
        if not _fk_exists(cursor, "stock_requisition", "stock_requisition_fournisseur_id_c2f1a425_fk_order_fou"):
            cursor.execute(
                "ALTER TABLE `stock_requisition` "
                "ADD CONSTRAINT `stock_requisition_fournisseur_id_c2f1a425_fk_order_fou` "
                "FOREIGN KEY (`fournisseur_id`) REFERENCES `order_fournisseur` (`id`) "
                "ON DELETE SET NULL"
            )
        if not _index_exists(cursor, "stock_requisition", "stock_req_ent_fou_idx"):
            cursor.execute(
                "CREATE INDEX `stock_req_ent_fou_idx` "
                "ON `stock_requisition` (`entreprise_id`, `fournisseur_id`)"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0044_requisition_fournisseur'),
        ('order', '0012_alter_commandeitem_quantite_alter_fraislot_montant_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(forwards, backwards),
            ],
        ),
    ]
