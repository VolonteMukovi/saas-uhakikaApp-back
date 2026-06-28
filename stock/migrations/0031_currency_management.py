from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stock', '0030_entreprise_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='detteclient',
            name='devise_reference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='dettes_reference', to='stock.devise'),
        ),
        migrations.AddField(
            model_name='detteclient',
            name='montant_reference',
            field=models.DecimalField(decimal_places=5, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='detteclient',
            name='taux_change',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='devise_reference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ligneentrees_reference', to='stock.devise'),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='montant_reference',
            field=models.DecimalField(decimal_places=5, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='ligneentree',
            name='taux_change',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True),
        ),
        migrations.AddField(
            model_name='lignesortie',
            name='devise_reference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='lignesorties_reference', to='stock.devise'),
        ),
        migrations.AddField(
            model_name='lignesortie',
            name='montant_reference',
            field=models.DecimalField(decimal_places=5, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='lignesortie',
            name='taux_change',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True),
        ),
        migrations.AddField(
            model_name='sortie',
            name='devise_reference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='sorties_reference', to='stock.devise'),
        ),
        migrations.CreateModel(
            name='TauxChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taux', models.DecimalField(decimal_places=8, max_digits=20)),
                ('date_application', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cree_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='taux_change_crees', to=settings.AUTH_USER_MODEL)),
                ('devise_cible', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taux_entrants', to='stock.devise')),
                ('devise_source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taux_sortants', to='stock.devise')),
                ('entreprise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taux_change', to='stock.entreprise')),
            ],
            options={
                'verbose_name': 'Taux de change',
                'verbose_name_plural': 'Taux de change',
                'ordering': ['-date_application', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='tauxchange',
            index=models.Index(fields=['entreprise_id', 'is_active'], name='stock_tauxc_entrepr_0d4a67_idx'),
        ),
        migrations.AddIndex(
            model_name='tauxchange',
            index=models.Index(fields=['entreprise_id', 'devise_source_id', 'devise_cible_id'], name='stock_tauxc_entrepr_4aa17d_idx'),
        ),
        migrations.AddIndex(
            model_name='tauxchange',
            index=models.Index(fields=['entreprise_id', 'date_application'], name='stock_tauxc_entrepr_77d803_idx'),
        ),
    ]
