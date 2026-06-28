from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0031_currency_management'),
        ('caisse', '0002_type_caisse_multi_caisse'),
    ]

    operations = [
        migrations.AddField(
            model_name='mouvementcaisse',
            name='devise_reference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='mouvements_caisse_reference', to='stock.devise'),
        ),
        migrations.AddField(
            model_name='mouvementcaisse',
            name='montant_reference',
            field=models.DecimalField(decimal_places=5, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='mouvementcaisse',
            name='taux_change',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True),
        ),
    ]
