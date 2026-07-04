from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0035_entreprise_configuration_complete'),
        ('caisse', '0004_mouvementcaisse_conversion_origine'),
    ]

    operations = [
        migrations.AddField(
            model_name='mouvementcaisse',
            name='montant_applique',
            field=models.DecimalField(
                blank=True, decimal_places=5, max_digits=14, null=True,
                help_text="Montant imputé sur l'objet lié (ex. dette) dans la devise métier de cet objet.",
            ),
        ),
        migrations.AddField(
            model_name='mouvementcaisse',
            name='devise_applique',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='mouvements_caisse_applique', to='stock.devise',
            ),
        ),
    ]
