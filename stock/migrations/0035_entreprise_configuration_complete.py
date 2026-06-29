# Generated manually for SaaS flow

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0034_rename_stock_sortie_client_hist_idx_stock_sorti_client__36a5f7_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='entreprise',
            name='configuration_complete',
            field=models.BooleanField(
                default=False,
                help_text="True lorsque les informations obligatoires de l'entreprise sont complétées (flow SaaS).",
            ),
        ),
    ]
