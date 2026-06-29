import uuid

from django.db import migrations, models


def remplir_references_paiement(apps, schema_editor):
    Paiement = apps.get_model('abonnements', 'PaiementAbonnement')
    for paiement in Paiement.objects.filter(reference_interne__isnull=True):
        paiement.reference_interne = str(uuid.uuid4())
        paiement.save(update_fields=['reference_interne'])


class Migration(migrations.Migration):

    dependencies = [
        ('abonnements', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='paiementabonnement',
            name='reference_interne',
            field=models.CharField(
                max_length=64,
                null=True,
                unique=True,
                help_text='Référence unique UHAKIKAAPP transmise au gateway.',
            ),
        ),
        migrations.AddField(
            model_name='paiementabonnement',
            name='url_paiement',
            field=models.URLField(blank=True),
        ),
        migrations.RunPython(remplir_references_paiement, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='paiementabonnement',
            name='reference_interne',
            field=models.CharField(
                max_length=64,
                unique=True,
                editable=False,
                help_text='Référence unique UHAKIKAAPP transmise au gateway.',
            ),
        ),
        migrations.CreateModel(
            name='JournalWebhookPaiement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fournisseur', models.CharField(max_length=30)),
                ('reference_interne', models.CharField(blank=True, max_length=64)),
                ('payload', models.JSONField(default=dict)),
                ('statut_traitement', models.CharField(
                    choices=[
                        ('recu', 'Reçu'),
                        ('traite', 'Traité'),
                        ('ignore', 'Ignoré'),
                        ('erreur', 'Erreur'),
                    ],
                    default='recu',
                    max_length=20,
                )),
                ('message', models.TextField(blank=True)),
                ('ip_source', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paiement', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name='webhooks',
                    to='abonnements.paiementabonnement',
                )),
            ],
            options={
                'verbose_name': 'Journal webhook paiement',
                'verbose_name_plural': 'Journal webhooks paiement',
                'ordering': ['-created_at'],
            },
        ),
    ]
