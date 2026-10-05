import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0052_inventaire_annulation_validation'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LogSuppression',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('article_nom', models.CharField(blank=True, default='', max_length=255)),
                ('sortie_numero', models.PositiveIntegerField(help_text='Numéro (id) de la sortie au moment de la suppression.')),
                ('quantite', models.DecimalField(decimal_places=5, default=0, max_digits=12)),
                ('prix_unitaire', models.DecimalField(blank=True, decimal_places=5, max_digits=12, null=True)),
                ('devise_sigle', models.CharField(blank=True, default='', max_length=10)),
                ('motif', models.CharField(choices=[('SORTIE_SUPPRIMEE', 'Vente supprimée'), ('LIGNE_SUPPRIMEE', 'Ligne de vente supprimée')], default='SORTIE_SUPPRIMEE', max_length=20)),
                ('utilisateur_nom', models.CharField(blank=True, default='', max_length=255)),
                ('date_suppression', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('article', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs_suppressions', to='stock.article')),
                ('entreprise', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs_suppressions', to='stock.entreprise')),
                ('succursale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs_suppressions', to='stock.succursale')),
                ('utilisateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs_suppressions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date_suppression', '-id'],
                'indexes': [
                    models.Index(fields=['entreprise', '-date_suppression'], name='logsupp_ent_date_idx'),
                    models.Index(fields=['entreprise', 'succursale', '-date_suppression'], name='logsupp_ent_succ_date_idx'),
                ],
            },
        ),
    ]
