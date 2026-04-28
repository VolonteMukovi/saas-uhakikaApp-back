from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stock", "0022_alter_mouvementcaisse_motif_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="beneficelot",
            name="quantite_vendue",
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),
        migrations.AlterField(
            model_name="ligneentree",
            name="quantite",
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),
        migrations.AlterField(
            model_name="ligneentree",
            name="quantite_restante",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                help_text="Quantité encore disponible dans ce lot (FIFO)",
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name="ligneentree",
            name="seuil_alerte",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                help_text="Seuil d'alerte pour cet article",
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name="lignesortie",
            name="quantite",
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),
        migrations.AlterField(
            model_name="lignesortielot",
            name="quantite",
            field=models.DecimalField(
                decimal_places=3,
                help_text="Quantité prélevée de ce lot",
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name="stock",
            name="Qte",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
        migrations.AlterField(
            model_name="stock",
            name="seuilAlert",
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
    ]
