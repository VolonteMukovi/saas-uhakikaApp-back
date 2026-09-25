# Generated manually for DettesClients performance / timestamps

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0047_dettes_clients_paiement'),
    ]

    operations = [
        migrations.AddField(
            model_name='dettesclients',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='paiementdettesclients',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name='dettesclients',
            index=models.Index(fields=['status', '-date', '-id'], name='stock_dette_status_2f8a1c_idx'),
        ),
        migrations.AddIndex(
            model_name='paiementdettesclients',
            index=models.Index(fields=['-id'], name='stock_paiem_id_desc_idx'),
        ),
    ]
