from django.db import migrations


def clear_entree_description_from_lot_closure(apps, schema_editor):
    Lot = apps.get_model("order", "Lot")
    Entree = apps.get_model("stock", "Entree")
    for lot in Lot.objects.exclude(entree_stock_id=None).iterator():
        Entree.objects.filter(pk=lot.entree_stock_id).update(description="")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0008_commande_nom"),
    ]

    operations = [
        migrations.RunPython(clear_entree_description_from_lot_closure, noop_reverse),
    ]
