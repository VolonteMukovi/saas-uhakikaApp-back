# Generated manually for CodeBarresArticle

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('stock', '0037_rename_conditionnement_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeBarresArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('code', models.CharField(max_length=128)),
                ('type_code', models.CharField(
                    choices=[
                        ('EAN13', 'EAN-13'),
                        ('EAN8', 'EAN-8'),
                        ('UPC', 'UPC'),
                        ('CODE128', 'Code 128'),
                        ('QR', 'QR'),
                        ('INTERNE', 'Interne'),
                        ('AUTRE', 'Autre'),
                    ],
                    default='INTERNE',
                    max_length=20,
                )),
                ('est_principal', models.BooleanField(default=False, help_text='Code principal du conditionnement.')),
                ('est_actif', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('article', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='codes_barres',
                    to='stock.article',
                )),
                ('conditionnement', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='codes_barres',
                    to='stock.conditionnementarticle',
                )),
                ('cree_par', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='codes_barres_crees',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('entreprise', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='codes_barres',
                    to='stock.entreprise',
                )),
                ('succursale', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='codes_barres',
                    to='stock.succursale',
                )),
            ],
            options={
                'ordering': ['article_id', 'conditionnement_id', '-est_principal', 'code'],
            },
        ),
        migrations.AddIndex(
            model_name='codebarresarticle',
            index=models.Index(fields=['entreprise', 'code'], name='stock_codeb_entrepr_8a1f2d_idx'),
        ),
        migrations.AddIndex(
            model_name='codebarresarticle',
            index=models.Index(
                fields=['entreprise', 'est_actif'],
                name='stock_codeb_entrepr_4c9e1a_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='codebarresarticle',
            index=models.Index(
                fields=['article', 'conditionnement'],
                name='stock_codeb_article_7b3f8e_idx',
            ),
        ),
        migrations.AddConstraint(
            model_name='codebarresarticle',
            constraint=models.UniqueConstraint(
                fields=('entreprise', 'code'),
                name='uniq_code_barres_entreprise_code',
            ),
        ),
    ]
