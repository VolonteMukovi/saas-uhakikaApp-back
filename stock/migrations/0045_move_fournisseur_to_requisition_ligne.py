# Generated manually — corrige l'écart DB vs migration 0044 réécrite.
# Ancienne 0044 (appliquée) : fournisseur sur stock_requisition.
# Nouvelle 0044 (fichiers) : fournisseur sur stock_requisitionligne.
# Cette migration aligne la base sans toucher l'état Django déjà cohérent.

from django.db import migrations


FORWARD_SQL = [
    # Retirer l'ancien lien au niveau document
    "ALTER TABLE `stock_requisition` DROP INDEX `stock_req_ent_fou_idx`",
    "ALTER TABLE `stock_requisition` DROP FOREIGN KEY `stock_requisition_fournisseur_id_c2f1a425_fk_order_fou`",
    "ALTER TABLE `stock_requisition` DROP COLUMN `fournisseur_id`",
    # Ajouter le lien par ligne / article
    (
        "ALTER TABLE `stock_requisitionligne` "
        "ADD COLUMN `fournisseur_id` BIGINT NULL, "
        "ADD CONSTRAINT `stock_requisitionligne_fournisseur_id_fk_order_fou` "
        "FOREIGN KEY (`fournisseur_id`) REFERENCES `order_fournisseur` (`id`) "
        "ON DELETE SET NULL"
    ),
    (
        "CREATE INDEX `stock_reqligne_fou_idx` "
        "ON `stock_requisitionligne` (`requisition_id`, `fournisseur_id`)"
    ),
]

REVERSE_SQL = [
    "ALTER TABLE `stock_requisitionligne` DROP INDEX `stock_reqligne_fou_idx`",
    "ALTER TABLE `stock_requisitionligne` DROP FOREIGN KEY `stock_requisitionligne_fournisseur_id_fk_order_fou`",
    "ALTER TABLE `stock_requisitionligne` DROP COLUMN `fournisseur_id`",
    (
        "ALTER TABLE `stock_requisition` "
        "ADD COLUMN `fournisseur_id` BIGINT NULL, "
        "ADD CONSTRAINT `stock_requisition_fournisseur_id_c2f1a425_fk_order_fou` "
        "FOREIGN KEY (`fournisseur_id`) REFERENCES `order_fournisseur` (`id`) "
        "ON DELETE SET NULL"
    ),
    (
        "CREATE INDEX `stock_req_ent_fou_idx` "
        "ON `stock_requisition` (`entreprise_id`, `fournisseur_id`)"
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0044_requisition_fournisseur'),
        ('order', '0012_alter_commandeitem_quantite_alter_fraislot_montant_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # L'état Django (via 0044 réécrite) correspond déjà aux modèles.
            state_operations=[],
            database_operations=[
                migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
            ],
        ),
    ]
