from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inscription', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(db_index=True, max_length=64, unique=True)),
                ('email_cible', models.EmailField(max_length=254)),
                ('cree_le', models.DateTimeField(auto_now_add=True)),
                ('expire_le', models.DateTimeField()),
                ('utilise_le', models.DateTimeField(blank=True, null=True)),
                ('invalide', models.BooleanField(default=False)),
                ('utilisateur', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='jetons_verification_email',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Jeton vérification e-mail',
                'verbose_name_plural': 'Jetons vérification e-mail',
                'ordering': ['-cree_le'],
                'indexes': [
                    models.Index(fields=['utilisateur', '-cree_le'], name='inscription_utilisa_8a1f2d_idx'),
                    models.Index(fields=['expire_le'], name='inscription_expire__4c9b1a_idx'),
                ],
            },
        ),
    ]
