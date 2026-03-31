# Supprime le modèle `Fournisseur` de l'app `stock` (désormais dans `order`).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("stock", "0018_fournisseur_code_blank"),
        ("order", "0004_fournisseur_in_order_app"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Fournisseur",
        ),
    ]
