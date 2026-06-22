from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0010_commande_sortie_livraison"),
    ]

    operations = [
        migrations.AlterField(
            model_name="commandeitem",
            name="quantite",
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),
        migrations.AlterField(
            model_name="lotitem",
            name="quantite",
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),
    ]
