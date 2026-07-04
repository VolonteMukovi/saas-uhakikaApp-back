from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0035_entreprise_configuration_complete'),
        ('caisse', '0003_mouvementcaisse_currency_snapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='mouvementcaisse',
            name='montant_origine',
            field=models.DecimalField(
                blank=True, decimal_places=5, max_digits=14, null=True,
                help_text="Montant d'origine avant conversion vers la devise de la caisse.",
            ),
        ),
        migrations.AddField(
            model_name='mouvementcaisse',
            name='devise_origine',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='mouvements_caisse_origine', to='stock.devise',
            ),
        ),
        migrations.AddField(
            model_name='mouvementcaisse',
            name='taux_conversion',
            field=models.DecimalField(
                blank=True, decimal_places=8, max_digits=20, null=True,
                help_text='Taux appliqué : 1 unité devise_origine = taux_conversion unités devise caisse.',
            ),
        ),
        migrations.AddField(
            model_name='mouvementcaisse',
            name='date_taux',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='Date du taux utilisé pour la conversion caisse.',
            ),
        ),
    ]
