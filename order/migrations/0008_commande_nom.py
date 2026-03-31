# Champ optionnel `nom` sur Commande (libellé / désignation provisoire).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0007_lot_closure_stock_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="commande",
            name="nom",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Libellé optionnel (ex. désignation provisoire si le catalogue n’est pas à jour).",
                max_length=255,
            ),
        ),
    ]
