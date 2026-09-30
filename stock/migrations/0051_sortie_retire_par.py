from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0050_repair_dettes_clients_schema'),
    ]

    operations = [
        migrations.AddField(
            model_name='sortie',
            name='retire_par',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Personne venue retirer la marchandise (vente à crédit uniquement, optionnel).',
                max_length=150,
            ),
        ),
    ]
