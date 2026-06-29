from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0032_rename_stock_tauxc_entrepr_0d4a67_idx_stock_tauxc_entrepr_a27464_idx_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='sortie',
            index=models.Index(
                fields=['client_id', 'entreprise_id', '-date_creation'],
                name='stock_sortie_client_hist_idx',
            ),
        ),
    ]
