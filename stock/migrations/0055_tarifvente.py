import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0054_lignesortie_pricing_audit'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TarifVente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prix', models.DecimalField(decimal_places=5, max_digits=14)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('article', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tarifs_vente',
                    to='stock.article',
                )),
                ('conditionnement', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tarifs_vente',
                    to='stock.conditionnementarticle',
                )),
                ('devise', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='tarifs_vente',
                    to='stock.devise',
                )),
                ('modifie_par', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='tarifs_vente_modifies',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['article_id', 'conditionnement_id'],
            },
        ),
        migrations.AddConstraint(
            model_name='tarifvente',
            constraint=models.UniqueConstraint(
                condition=models.Q(('conditionnement__isnull', False)),
                fields=('article', 'conditionnement'),
                name='uniq_tarif_vente_article_conditionnement',
            ),
        ),
        migrations.AddConstraint(
            model_name='tarifvente',
            constraint=models.UniqueConstraint(
                condition=models.Q(('conditionnement__isnull', True)),
                fields=('article',),
                name='uniq_tarif_vente_article_base',
            ),
        ),
        migrations.AddIndex(
            model_name='tarifvente',
            index=models.Index(fields=['article', 'conditionnement'], name='stock_tarif_article_cond_idx'),
        ),
        migrations.AddIndex(
            model_name='tarifvente',
            index=models.Index(fields=['updated_at'], name='stock_tarif_updated_idx'),
        ),
    ]
