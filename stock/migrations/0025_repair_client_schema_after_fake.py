from django.db import migrations


def _column_names(connection, table_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    names = set()
    for column in description:
        names.add(getattr(column, 'name', column[0]))
    return names


def repair_client_schema(apps, schema_editor):
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())

    Client = apps.get_model('stock', 'Client')
    ClientEntreprise = apps.get_model('stock', 'ClientEntreprise')

    client_table = Client._meta.db_table
    client_entreprise_table = ClientEntreprise._meta.db_table

    if client_table not in tables:
        return

    client_columns = _column_names(connection, client_table)

    if 'password' not in client_columns:
        schema_editor.add_field(Client, Client._meta.get_field('password'))
        client_columns = _column_names(connection, client_table)

    if client_entreprise_table not in tables:
        schema_editor.create_model(ClientEntreprise)
        tables = set(connection.introspection.table_names())

    legacy_columns = {'entreprise_id', 'succursale_id', 'is_special'}
    if legacy_columns.issubset(client_columns) and client_entreprise_table in tables:
        qn = schema_editor.quote_name
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT IGNORE INTO {qn(client_entreprise_table)}
                    (client_id, entreprise_id, succursale_id, is_special)
                SELECT
                    id,
                    entreprise_id,
                    succursale_id,
                    COALESCE(is_special, 0)
                FROM {qn(client_table)}
                WHERE entreprise_id IS NOT NULL
                """
            )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('stock', '0024_alter_beneficelot_benefice_total_and_more'),
    ]

    operations = [
        migrations.RunPython(repair_client_schema, migrations.RunPython.noop),
    ]