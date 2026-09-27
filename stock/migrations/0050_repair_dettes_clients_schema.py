"""Répare le schéma DettesClients si migrations 0047–0049 ont été faked / DDL manquant."""

from django.db import migrations, models
import django.utils.timezone


def _index_names(connection, table_name):
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table_name)
    return set(constraints.keys())


def _column_names(connection, table_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    names = set()
    for column in description:
        names.add(getattr(column, 'name', column[0]))
    return names


def repair_dettes_clients_schema(apps, schema_editor):
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())

    DettesClients = apps.get_model('stock', 'DettesClients')
    PaiementDettesClients = apps.get_model('stock', 'PaiementDettesClients')
    dette_table = DettesClients._meta.db_table
    paiement_table = PaiementDettesClients._meta.db_table

    if dette_table not in tables:
        schema_editor.create_model(DettesClients)
        tables = set(connection.introspection.table_names())

    if paiement_table not in tables:
        schema_editor.create_model(PaiementDettesClients)
        tables = set(connection.introspection.table_names())

    if dette_table in tables:
        cols = _column_names(connection, dette_table)
        if 'updated_at' not in cols:
            field = models.DateTimeField(auto_now=True)
            field.set_attributes_from_name('updated_at')
            schema_editor.add_field(DettesClients, field)

        indexes = _index_names(connection, dette_table)
        wanted = {
            'stock_dette_date_0965c0_idx': models.Index(fields=['date'], name='stock_dette_date_0965c0_idx'),
            'stock_dette_status_ee0840_idx': models.Index(fields=['status'], name='stock_dette_status_ee0840_idx'),
            'stock_dette_date_53d584_idx': models.Index(
                fields=['date', 'status'], name='stock_dette_date_53d584_idx'
            ),
            'stock_dette_status_6c1738_idx': models.Index(
                fields=['status', '-date', '-id'], name='stock_dette_status_6c1738_idx'
            ),
        }
        for name, index in wanted.items():
            if name not in indexes:
                schema_editor.add_index(DettesClients, index)

    if paiement_table in tables:
        cols = _column_names(connection, paiement_table)
        if 'created_at' not in cols:
            field = models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)
            field.set_attributes_from_name('created_at')
            schema_editor.add_field(PaiementDettesClients, field)

        indexes = _index_names(connection, paiement_table)
        wanted = {
            'stock_paiem_date_3bc5d2_idx': models.Index(fields=['date'], name='stock_paiem_date_3bc5d2_idx'),
            'stock_paiem_dettes__c82807_idx': models.Index(
                fields=['dettes_clients', 'date'], name='stock_paiem_dettes__c82807_idx'
            ),
            'stock_paiem_id_b2a244_idx': models.Index(fields=['-id'], name='stock_paiem_id_b2a244_idx'),
        }
        for name, index in wanted.items():
            if name not in indexes:
                schema_editor.add_index(PaiementDettesClients, index)


class Migration(migrations.Migration):
    """
    Idempotent repair: create DettesClients / PaiementDettesClients + timestamps/indexes
    when django_migrations says 0047–0049 applied but tables/columns are missing.
    """

    atomic = False

    dependencies = [
        ('stock', '0049_rename_stock_dette_status_2f8a1c_idx_stock_dette_status_6c1738_idx_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(repair_dettes_clients_schema, migrations.RunPython.noop),
            ],
        ),
    ]
