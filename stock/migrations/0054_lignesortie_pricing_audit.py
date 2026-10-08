import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0053_logsuppression'),
    ]

    operations = [
        migrations.AddField(
            model_name='lignesortie',
            name='conditionnement',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='lignes_sortie',
                to='stock.conditionnementarticle',
            ),
        ),
        migrations.AddField(
            model_name='lignesortie',
            name='motif_prix_exception',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='lignesortie',
            name='quantite_conditionnement',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='lignesortie',
            name='prix_conditionnement',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name='lignesortie',
            name='montant_total',
            field=models.DecimalField(blank=True, decimal_places=5, max_digits=14, null=True),
        ),
    ]
