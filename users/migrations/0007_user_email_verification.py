from django.db import migrations, models


def marquer_comptes_existants_verifies(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(is_active=True).update(email_verifie=True)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_verifie',
            field=models.BooleanField(
                default=False,
                help_text="True lorsque l'utilisateur a confirmé son adresse e-mail UHAKIKAAPP.",
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='message_bienvenue_envoye',
            field=models.BooleanField(
                default=False,
                help_text="True après envoi unique de l'e-mail de bienvenue post-configuration.",
            ),
        ),
        migrations.RunPython(marquer_comptes_existants_verifies, migrations.RunPython.noop),
    ]
