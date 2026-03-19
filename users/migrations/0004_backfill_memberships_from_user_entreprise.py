from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Membership = apps.get_model('users', 'Membership')

    # Créer un Membership pour chaque user qui a déjà une entreprise
    for u in User.objects.exclude(entreprise_id__isnull=True).iterator():
        Membership.objects.get_or_create(
            user_id=u.id,
            entreprise_id=u.entreprise_id,
            defaults={
                'role': 'admin' if getattr(u, 'role', None) == 'admin' else 'user',
                'is_active': True,
            }
        )


def backwards(apps, schema_editor):
    # On ne supprime pas automatiquement les memberships (risque de perte).
    # Migration réversible volontairement no-op.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0003_membership_userbranch'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

