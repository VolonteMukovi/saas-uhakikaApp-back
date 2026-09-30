"""Crée la table du cache partagé (idempotence, limite chatbot) via `createcachetable`."""
from django.core.management import call_command
from django.db import migrations


def creer_table_cache(apps, schema_editor):
    call_command('createcachetable', database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.RunPython(creer_table_cache, migrations.RunPython.noop),
    ]
