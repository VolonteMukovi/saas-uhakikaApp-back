from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0029_move_caisse_to_app'),
    ]

    operations = [
        migrations.AddField(
            model_name='entreprise',
            name='config',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Configuration JSON (apparence rapports, POS, UI…)',
            ),
        ),
    ]
