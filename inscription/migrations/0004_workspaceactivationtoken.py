from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inscription', '0003_email_envoi_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkspaceActivationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(db_index=True, max_length=64, unique=True)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('expire_le', models.DateTimeField()),
                ('utilise_le', models.DateTimeField(blank=True, null=True)),
                ('invalide', models.BooleanField(default=False)),
                ('utilisateur', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='jetons_activation_espace',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Jeton activation espace',
                'verbose_name_plural': 'Jetons activation espace',
                'ordering': ['-cree_le'],
                'indexes': [
                    models.Index(fields=['utilisateur', '-cree_le'], name='inscription_utilisa_8f0a2d_idx'),
                    models.Index(fields=['expire_le'], name='inscription_expire__a1b2c3_idx'),
                ],
            },
        ),
    ]
