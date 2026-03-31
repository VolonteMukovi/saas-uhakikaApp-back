# Entrée de stock liée au lot (clôture) — pas de champs d'appro sur LotItem (payload API uniquement).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stock", "0001_initial"),
        ("order", "0006_rename_order_commande_entreprise_client_statut_idx_order_comma_entrepr_c8fef6_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="lot",
            name="entree_stock",
            field=models.ForeignKey(
                blank=True,
                help_text="Entrée de stock générée à la clôture (tracabilité, pas d'entrée avant clôture).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lots_transit_origine",
                to="stock.entree",
            ),
        ),
    ]
